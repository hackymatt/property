"use client";
import { ThemeProvider, createTheme, CssBaseline } from "@mui/material";
import { useMemo, useState, createContext, useContext } from "react";

const ColorModeContext = createContext({ toggle: () => {} });
export const useColorMode = () => useContext(ColorModeContext);

export default function ThemeRegistry({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mode, setMode] = useState<"light" | "dark">("light");
  const colorMode = useMemo(
    () => ({ toggle: () => setMode((m) => (m === "light" ? "dark" : "light")) }),
    []
  );
  const theme = useMemo(
    () =>
      createTheme({
        palette: { mode },
        typography: { fontFamily: "Roboto, sans-serif" },
      }),
    [mode]
  );
  return (
    <ColorModeContext.Provider value={colorMode}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}
