import 'dart:math';

import 'package:meta/meta.dart';

/// What a generated password should look like.
@immutable
final class PasswordRecipe {
  const PasswordRecipe({
    this.length = 20,
    this.uppercase = true,
    this.lowercase = true,
    this.digits = true,
    this.symbols = true,
    this.avoidAmbiguous = false,
  });

  /// Shortest password the generator will make.
  static const int minLength = 8;

  /// Longest password the generator will make.
  static const int maxLength = 128;

  /// Characters that are easy to confuse when read aloud or retyped.
  static const String ambiguous = 'Il1O0o';

  /// How many characters to generate.
  final int length;

  /// Include A-Z.
  final bool uppercase;

  /// Include a-z.
  final bool lowercase;

  /// Include 0-9.
  final bool digits;

  /// Include punctuation.
  final bool symbols;

  /// Leave out characters that are easily mistaken for one another.
  final bool avoidAmbiguous;

  /// True when at least one character set is selected.
  bool get hasAnyCharacterSet => uppercase || lowercase || digits || symbols;

  /// A copy with the given changes.
  PasswordRecipe copyWith({
    int? length,
    bool? uppercase,
    bool? lowercase,
    bool? digits,
    bool? symbols,
    bool? avoidAmbiguous,
  }) => PasswordRecipe(
    length: length ?? this.length,
    uppercase: uppercase ?? this.uppercase,
    lowercase: lowercase ?? this.lowercase,
    digits: digits ?? this.digits,
    symbols: symbols ?? this.symbols,
    avoidAmbiguous: avoidAmbiguous ?? this.avoidAmbiguous,
  );
}

/// What a generated passphrase should look like.
@immutable
final class PassphraseRecipe {
  const PassphraseRecipe({
    this.wordCount = 5,
    this.separator = '-',
    this.capitalise = false,
    this.includeNumber = false,
  });

  /// Fewest words the generator will use.
  ///
  /// Four words from this list is about 51 bits of entropy, which is the point
  /// below which a passphrase stops being a serious choice.
  static const int minWords = 3;

  /// Most words the generator will use.
  static const int maxWords = 12;

  /// Number of words.
  final int wordCount;

  /// What goes between the words.
  final String separator;

  /// Capitalise the first letter of each word.
  final bool capitalise;

  /// Append a digit, which some sites insist on.
  final bool includeNumber;

  /// A copy with the given changes.
  PassphraseRecipe copyWith({
    int? wordCount,
    String? separator,
    bool? capitalise,
    bool? includeNumber,
  }) => PassphraseRecipe(
    wordCount: wordCount ?? this.wordCount,
    separator: separator ?? this.separator,
    capitalise: capitalise ?? this.capitalise,
    includeNumber: includeNumber ?? this.includeNumber,
  );
}

/// Generates passwords, passphrases and usernames.
///
/// Every draw comes from [Random.secure], which is the platform's
/// cryptographically secure source. The default generator in `dart:math` is
/// seeded predictably and would make generated passwords guessable, so it is
/// never used here.
final class PasswordGenerator {
  /// Uses the platform's secure random source.
  PasswordGenerator() : _random = Random.secure();

  /// Uses a caller-supplied source. For tests that need repeatable output.
  ///
  /// Never use this in the application: a predictable source produces
  /// predictable passwords.
  @visibleForTesting
  PasswordGenerator.withRandom(this._random);

  final Random _random;

  static const String _uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  static const String _lowercase = 'abcdefghijklmnopqrstuvwxyz';
  static const String _digits = '0123456789';
  static const String _symbols = '!#%&*+-=?@^_~';

  /// Builds a password from [recipe].
  ///
  /// Guarantees at least one character from every selected set, which is what
  /// sites mean when they demand "a number and a symbol". The required
  /// characters are placed first and then the whole string is shuffled, so
  /// their positions are not predictable.
  ///
  /// Throws [ArgumentError] when the recipe asks for nothing or for a length
  /// outside the permitted range.
  String password(PasswordRecipe recipe) {
    if (!recipe.hasAnyCharacterSet) {
      throw ArgumentError.value(
        recipe,
        'recipe',
        'At least one character set must be selected',
      );
    }
    if (recipe.length < PasswordRecipe.minLength ||
        recipe.length > PasswordRecipe.maxLength) {
      throw ArgumentError.value(
        recipe.length,
        'recipe.length',
        'Must be between ${PasswordRecipe.minLength} and '
            '${PasswordRecipe.maxLength}',
      );
    }

    final List<String> pools = <String>[
      if (recipe.uppercase) _filter(_uppercase, recipe.avoidAmbiguous),
      if (recipe.lowercase) _filter(_lowercase, recipe.avoidAmbiguous),
      if (recipe.digits) _filter(_digits, recipe.avoidAmbiguous),
      if (recipe.symbols) _filter(_symbols, recipe.avoidAmbiguous),
    ].where((String pool) => pool.isNotEmpty).toList();

    if (pools.isEmpty) {
      throw ArgumentError.value(
        recipe,
        'recipe',
        'Excluding ambiguous characters left no characters to choose from',
      );
    }

    final String combined = pools.join();
    final List<String> characters = <String>[
      // One from each pool, so every selected set really appears.
      for (final String pool in pools) pool[_random.nextInt(pool.length)],
      // The rest drawn from everything selected.
      for (int i = pools.length; i < recipe.length; i++)
        combined[_random.nextInt(combined.length)],
    ];

    // Fisher-Yates, so the guaranteed characters are not always at the front.
    for (int i = characters.length - 1; i > 0; i--) {
      final int j = _random.nextInt(i + 1);
      final String swap = characters[i];
      characters[i] = characters[j];
      characters[j] = swap;
    }
    return characters.join();
  }

  /// Builds a passphrase from [recipe].
  String passphrase(PassphraseRecipe recipe) {
    final int words = recipe.wordCount.clamp(
      PassphraseRecipe.minWords,
      PassphraseRecipe.maxWords,
    );
    final List<String> chosen = <String>[
      for (int i = 0; i < words; i++)
        _transform(wordList[_random.nextInt(wordList.length)], recipe),
    ];
    final String phrase = chosen.join(recipe.separator);
    if (!recipe.includeNumber) {
      return phrase;
    }
    return '$phrase${recipe.separator}${_random.nextInt(10000)}';
  }

  /// Builds a username: two words and a short number.
  String username() {
    final String first = wordList[_random.nextInt(wordList.length)];
    final String second = wordList[_random.nextInt(wordList.length)];
    return '$first.$second${_random.nextInt(1000)}';
  }

  String _transform(String word, PassphraseRecipe recipe) =>
      recipe.capitalise ? word[0].toUpperCase() + word.substring(1) : word;

  static String _filter(String pool, bool avoidAmbiguous) {
    if (!avoidAmbiguous) {
      return pool;
    }
    final StringBuffer buffer = StringBuffer();
    for (int i = 0; i < pool.length; i++) {
      if (!PasswordRecipe.ambiguous.contains(pool[i])) {
        buffer.write(pool[i]);
      }
    }
    return buffer.toString();
  }

  /// Word list for passphrases: short, common, unambiguous English words.
  ///
  /// 256 words, so each word contributes exactly 8 bits. A five-word
  /// passphrase is therefore 40 bits from the words alone — which is why the
  /// interface recommends a longer phrase or a generated password for a master
  /// password, and why the number option exists.
  static const List<String> wordList = <String>[
    'able',
    'acid',
    'acorn',
    'actor',
    'adapt',
    'adult',
    'afraid',
    'agency',
    'agree',
    'ahead',
    'alarm',
    'album',
    'alert',
    'alien',
    'alive',
    'alley',
    'alloy',
    'almond',
    'alone',
    'alpha',
    'amber',
    'amuse',
    'anchor',
    'angle',
    'ankle',
    'answer',
    'antique',
    'anvil',
    'apple',
    'april',
    'apron',
    'arcade',
    'arch',
    'arena',
    'argue',
    'armour',
    'arrow',
    'artist',
    'aspect',
    'asset',
    'atlas',
    'attic',
    'auburn',
    'audio',
    'august',
    'aunt',
    'autumn',
    'avenue',
    'awake',
    'award',
    'bacon',
    'badge',
    'bagel',
    'baker',
    'balance',
    'balloon',
    'bamboo',
    'banana',
    'banjo',
    'barley',
    'basil',
    'basket',
    'batch',
    'beacon',
    'beam',
    'bean',
    'bear',
    'beaver',
    'bedrock',
    'beetle',
    'begin',
    'behave',
    'bellow',
    'belt',
    'bench',
    'berry',
    'bicycle',
    'binder',
    'birch',
    'bishop',
    'bison',
    'blade',
    'blanket',
    'blend',
    'blossom',
    'blue',
    'board',
    'bobcat',
    'bolt',
    'bonus',
    'book',
    'boots',
    'border',
    'bottle',
    'boulder',
    'bounce',
    'bowl',
    'boxer',
    'bracket',
    'braid',
    'branch',
    'brass',
    'bread',
    'breeze',
    'brick',
    'bridge',
    'bright',
    'bronze',
    'brook',
    'brush',
    'bubble',
    'bucket',
    'buffalo',
    'bugle',
    'builder',
    'bulb',
    'bundle',
    'bunker',
    'burrow',
    'bushel',
    'butter',
    'button',
    'cabin',
    'cable',
    'cactus',
    'cadet',
    'camel',
    'camera',
    'campus',
    'candle',
    'canoe',
    'canvas',
    'canyon',
    'carbon',
    'cargo',
    'carpet',
    'carrot',
    'castle',
    'catalog',
    'cattle',
    'cedar',
    'celery',
    'cement',
    'census',
    'chalk',
    'charm',
    'cheese',
    'cherry',
    'chess',
    'chime',
    'chisel',
    'cider',
    'cinema',
    'circle',
    'citrus',
    'clamp',
    'clay',
    'clever',
    'cliff',
    'cloak',
    'clock',
    'cloud',
    'clover',
    'cobalt',
    'cocoa',
    'coffee',
    'collar',
    'colony',
    'column',
    'comet',
    'compass',
    'copper',
    'coral',
    'cork',
    'corner',
    'cotton',
    'county',
    'cousin',
    'cowboy',
    'crane',
    'crate',
    'crayon',
    'cream',
    'creek',
    'crest',
    'cricket',
    'crimson',
    'crisp',
    'crown',
    'crystal',
    'cube',
    'cuckoo',
    'cupcake',
    'curtain',
    'cushion',
    'cycle',
    'dagger',
    'dairy',
    'daisy',
    'damson',
    'dancer',
    'danger',
    'dapple',
    'daring',
    'dawn',
    'decade',
    'deck',
    'decoy',
    'deer',
    'delta',
    'denim',
    'dentist',
    'desert',
    'design',
    'dessert',
    'detail',
    'diamond',
    'diary',
    'dinner',
    'dipper',
    'doctor',
    'dolphin',
    'domino',
    'donkey',
    'donut',
    'double',
    'dragon',
    'drapery',
    'dresser',
    'drift',
    'drummer',
    'dugout',
    'dune',
    'dusk',
    'eagle',
    'easel',
    'echo',
    'eclipse',
    'edge',
    'effort',
    'eight',
    'elbow',
    'elder',
    'electric',
    'elegant',
    'elephant',
    'eleven',
    'elm',
    'ember',
    'emerald',
    'empire',
    'engine',
    'enjoy',
    'envelope',
    'equal',
    'escape',
  ];
}
