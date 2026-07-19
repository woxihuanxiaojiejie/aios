import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["frontend/src/**/*.{ts,tsx}"],
    plugins: {
      "react-hooks": reactHooks,
    },
    languageOptions: {
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        document: "readonly",
        fetch: "readonly",
        HTMLElement: "readonly",
        HTMLDivElement: "readonly",
        ResizeObserver: "readonly",
        window: "readonly",
      },
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
    },
  },
];
