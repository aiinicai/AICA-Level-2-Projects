import fs from "fs";

// 1. Fix sidebar.tsx Math.random
const sidebarPath = "src/components/ui/sidebar.tsx";
if (fs.existsSync(sidebarPath)) {
  let content = fs.readFileSync(sidebarPath, "utf8");
  content = content.replace(
    /const width = React\.useMemo\(\(\) => \{\s*return `\$\{Math\.floor\(Math\.random\(\) \* 40\) \+ 50\%\}`;\s*\}, \[\]\);/,
    'const width = "70%";',
  );
  fs.writeFileSync(sidebarPath, content, "utf8");
  console.log("Fixed sidebar.tsx");
}

// 2. Fix group.$groupId.tsx invite link SSR mismatch
const groupPath = "src/routes/_authenticated/group.$groupId.tsx";
if (fs.existsSync(groupPath)) {
  let content = fs.readFileSync(groupPath, "utf8");
  if (!content.includes("const [mounted, setMounted]")) {
    content = content.replace(
      /const \{/,
      "const [mounted, setMounted] = React.useState(false);\n  React.useEffect(() => setMounted(true), []);\n  const {\n",
    );
  }
  content = content.replace(
    /const link =\s*typeof window !== "undefined" \? `\$\{window\.location\.origin\}\/join\/\$\{group\.invite_code\}` : "";/,
    'const link = mounted ? `${window.location.origin}/join/${group.invite_code}` : "";',
  );
  fs.writeFileSync(groupPath, content, "utf8");
  console.log("Fixed group.$groupId.tsx");
}
