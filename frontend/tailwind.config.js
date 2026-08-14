/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#141B2D",
        sheet: "#FBFAF7",
        rule: "#D8D4CA",
        stamp: "#C2402E",
        seal: "#1F5C4A",
        graph: "#657388",
        maroon: "#891437",
        maroonDark: "#4D1525",
        gold: "#FFB81C",
      },
      fontFamily: {
        display: ["Oswald", "sans-serif"],
        body: ["Source Sans 3", "sans-serif"],
        data: ["JetBrains Mono", "monospace"],
      },
      fontSize: {
        xs: "12px",
        sm: "14px",
        base: "16px",
        lg: "20px",
        xl: "28px",
        "2xl": "40px",
        "3xl": "56px",
      },
      borderRadius: {
        DEFAULT: "2px",
      },
    },
  },
  plugins: [],
}

