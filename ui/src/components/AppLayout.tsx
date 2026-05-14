"use client";
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  AppBar, Toolbar, Typography, IconButton, Divider, Chip,
} from "@mui/material";
import DnsIcon from "@mui/icons-material/Dns";
import CodeIcon from "@mui/icons-material/Code";
import WorkIcon from "@mui/icons-material/Work";
import ScheduleIcon from "@mui/icons-material/Schedule";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import HistoryIcon from "@mui/icons-material/History";
import LogoutIcon from "@mui/icons-material/Logout";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import { useRouter, usePathname } from "next/navigation";
import { useColorMode } from "@/app/ThemeRegistry";
import { useEffect, useState } from "react";

const DRAWER_WIDTH = 220;

const NAV = [
  { label: "Domains", href: "/domains", icon: <DnsIcon /> },
  { label: "Sources", href: "/sources", icon: <CodeIcon /> },
  { label: "Jobs", href: "/jobs", icon: <WorkIcon /> },
  { label: "Schedules", href: "/schedules", icon: <ScheduleIcon /> },
  { label: "Run Log", href: "/run-log", icon: <ReceiptLongIcon /> },
  { label: "Schedule Log", href: "/schedule-log", icon: <HistoryIcon /> },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { toggle } = useColorMode();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    router.push("/login");
  };

  if (!ready) return null;

  return (
    <Box sx={{ display: "flex", height: "100vh" }}>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          "& .MuiDrawer-paper": { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar>
          <Typography variant="subtitle1" fontWeight={700}>
            Property Admin
          </Typography>
        </Toolbar>
        <Divider />
        <List dense>
          {NAV.map((item) => (
            <ListItemButton
              key={item.href}
              selected={pathname.startsWith(item.href)}
              onClick={() => router.push(item.href)}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>

      <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <AppBar position="static" color="default" elevation={1}>
          <Toolbar variant="dense">
            <Typography variant="subtitle2" sx={{ flexGrow: 1, textTransform: "capitalize" }}>
              {NAV.find((n) => pathname.startsWith(n.href))?.label ?? ""}
            </Typography>
            <Chip
              label={typeof window !== "undefined" ? localStorage.getItem("username") ?? "" : ""}
              size="small"
              sx={{ mr: 1 }}
            />
            <IconButton size="small" onClick={toggle}>
              <Brightness4Icon fontSize="small" />
            </IconButton>
            <IconButton size="small" onClick={logout}>
              <LogoutIcon fontSize="small" />
            </IconButton>
          </Toolbar>
        </AppBar>
        <Box sx={{ flexGrow: 1, overflow: "auto", p: 2 }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}
