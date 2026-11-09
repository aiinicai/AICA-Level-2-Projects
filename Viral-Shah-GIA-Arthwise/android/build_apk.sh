#!/usr/bin/env bash
set -e

# ==============================================================================
# GIA_Arthwise Loan Facilitator - Native Android APK Build Script
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$PROJECT_DIR/.." && pwd)"

echo "======================================================================"
echo " Building GIA_Arthwise Loan Facilitator Android APK"
echo "======================================================================"

# 1. Detect Java Home
if [ -z "$JAVA_HOME" ]; then
    if [ -d "$HOME/.bubblewrap/jdk/jdk-17.0.11+9/Contents/Home" ]; then
        export JAVA_HOME="$HOME/.bubblewrap/jdk/jdk-17.0.11+9/Contents/Home"
    elif [ -x "/usr/libexec/java_home" ]; then
        export JAVA_HOME="$(/usr/libexec/java_home 2>/dev/null || true)"
    fi
fi

if [ -z "$JAVA_HOME" ] || [ ! -d "$JAVA_HOME" ]; then
    echo "ERROR: JAVA_HOME is not set and could not be detected."
    echo "Please set JAVA_HOME or install OpenJDK 17."
    exit 1
fi
echo "✓ Using Java: $JAVA_HOME"

# 2. Detect Android SDK
if [ -z "$ANDROID_HOME" ]; then
    if [ -d "$HOME/.bubblewrap/android_sdk" ]; then
        export ANDROID_HOME="$HOME/.bubblewrap/android_sdk"
    elif [ -d "$HOME/Library/Android/sdk" ]; then
        export ANDROID_HOME="$HOME/Library/Android/sdk"
    fi
fi

if [ -z "$ANDROID_HOME" ] || [ ! -d "$ANDROID_HOME" ]; then
    echo "ERROR: ANDROID_HOME is not set and could not be detected."
    echo "Please set ANDROID_HOME to your Android SDK directory."
    exit 1
fi
echo "✓ Using Android SDK: $ANDROID_HOME"

# Find build-tools and android.jar
BUILD_TOOLS_DIR="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort -V | tail -n 1)"
if [ -z "$BUILD_TOOLS_DIR" ]; then
    echo "ERROR: No build-tools found in $ANDROID_HOME/build-tools"
    exit 1
fi
echo "✓ Using Build Tools: $BUILD_TOOLS_DIR"

ANDROID_JAR="$(find "$ANDROID_HOME/platforms" -name "android.jar" 2>/dev/null | sort -V | tail -n 1)"
if [ -z "$ANDROID_JAR" ]; then
    echo "ERROR: No android.jar found in $ANDROID_HOME/platforms"
    exit 1
fi
echo "✓ Using Platform JAR: $ANDROID_JAR"

# Tools
AAPT="$BUILD_TOOLS_DIR/aapt"
D8="$BUILD_TOOLS_DIR/d8"
ZIPALIGN="$BUILD_TOOLS_DIR/zipalign"
APKSIGNER="$BUILD_TOOLS_DIR/apksigner"
JAVAC="$JAVA_HOME/bin/javac"
KEYTOOL="$JAVA_HOME/bin/keytool"

# Verify required binaries
for tool in "$AAPT" "$D8" "$ZIPALIGN" "$APKSIGNER" "$JAVAC" "$KEYTOOL"; do
    if [ ! -x "$tool" ]; then
        echo "ERROR: Required tool not executable: $tool"
        exit 1
    fi
done

# Prepare working directories
BUILD_DIR="$PROJECT_DIR/build"
GEN_DIR="$BUILD_DIR/gen"
OBJ_DIR="$BUILD_DIR/obj"
BIN_DIR="$PROJECT_DIR/bin"

rm -rf "$BUILD_DIR"
mkdir -p "$GEN_DIR" "$OBJ_DIR" "$BIN_DIR"

# Ensure frontend assets are synced
echo "Syncing frontend web assets into Android assets/www..."
mkdir -p "$PROJECT_DIR/assets/www"
if [ -d "$WORKSPACE_ROOT/frontend/dist" ]; then
    cp -r "$WORKSPACE_ROOT/frontend/dist/"* "$PROJECT_DIR/assets/www/"
fi

# Step 1: Generate R.java
echo "Step 1: Generating R.java..."
"$AAPT" package -f -m \
    -J "$GEN_DIR" \
    -M "$PROJECT_DIR/AndroidManifest.xml" \
    -S "$PROJECT_DIR/res" \
    -I "$ANDROID_JAR"

# Step 2: Compile Java source files
echo "Step 2: Compiling Java source files..."
JAVA_FILES="$(find "$PROJECT_DIR/src" "$GEN_DIR" -name "*.java")"
"$JAVAC" -source 1.8 -target 1.8 \
    -bootclasspath "$ANDROID_JAR" \
    -d "$OBJ_DIR" \
    $JAVA_FILES

# Step 3: Convert compiled classes to Dalvik Executable (classes.dex)
echo "Step 3: Compiling classes to DEX with D8..."
CLASS_FILES="$(find "$OBJ_DIR" -name "*.class")"
"$D8" --min-api 26 \
    --output "$BUILD_DIR" \
    $CLASS_FILES

# Step 4: Package resources and assets into unsigned APK
echo "Step 4: Packaging resources into APK..."
"$AAPT" package -f \
    -M "$PROJECT_DIR/AndroidManifest.xml" \
    -S "$PROJECT_DIR/res" \
    -A "$PROJECT_DIR/assets" \
    -I "$ANDROID_JAR" \
    -F "$BUILD_DIR/app-unsigned.apk"

# Add classes.dex to APK
cd "$BUILD_DIR"
"$AAPT" add "app-unsigned.apk" classes.dex
cd "$PROJECT_DIR"

# Step 5: Align the APK (4-byte alignment)
echo "Step 5: Aligning APK with zipalign..."
"$ZIPALIGN" -f -p 4 \
    "$BUILD_DIR/app-unsigned.apk" \
    "$BUILD_DIR/app-unaligned.apk"

# Step 6: Create keystore if not exists and sign
KEYSTORE="$PROJECT_DIR/giaarthwise-release.keystore"
if [ ! -f "$KEYSTORE" ]; then
    echo "Creating release signing key..."
    "$KEYTOOL" -genkey -v \
        -keystore "$KEYSTORE" \
        -alias giaarthwise \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -storepass giaarthwise123 \
        -keypass giaarthwise123 \
        -dname "CN=GIA_Arthwise Loan Syndication, OU=Engineering, O=GIA_Arthwise, L=Vadodara, ST=Gujarat, C=IN"
fi

FINAL_APK="$BIN_DIR/giaarthwise-loan-facilitator.apk"

echo "Step 6: Signing APK with apksigner..."
"$APKSIGNER" sign \
    --ks "$KEYSTORE" \
    --ks-pass pass:giaarthwise123 \
    --out "$FINAL_APK" \
    "$BUILD_DIR/app-unaligned.apk"

# Step 7: Verify signature
echo "Step 7: Verifying signed APK..."
"$APKSIGNER" verify -v "$FINAL_APK"

echo "======================================================================"
echo " SUCCESS! Android APK created successfully:"
echo " File: $FINAL_APK"
echo " Size: $(du -h "$FINAL_APK" | cut -f1)"
echo "======================================================================"
