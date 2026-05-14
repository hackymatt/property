"use client";
import { useState, useCallback } from "react";
import { Menu, MenuItem, ListItemIcon, ListItemText } from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import type { CellContextMenuEvent } from "ag-grid-community";

interface MenuState {
  mouseX: number;
  mouseY: number;
  value: string;
}

export function useCellContextMenu() {
  const [menu, setMenu] = useState<MenuState | null>(null);

  const onCellContextMenu = useCallback((e: CellContextMenuEvent) => {
    const mouseEvent = e.event as MouseEvent | null;
    if (!mouseEvent) return;
    mouseEvent.preventDefault();
    setMenu({
      mouseX: mouseEvent.clientX,
      mouseY: mouseEvent.clientY,
      value: e.value == null ? "" : String(e.value),
    });
  }, []);

  const handleClose = useCallback(() => setMenu(null), []);

  const handleCopy = useCallback(() => {
    if (menu) navigator.clipboard.writeText(menu.value);
    setMenu(null);
  }, [menu]);

  const contextMenu = menu ? (
    <Menu
      open
      onClose={handleClose}
      anchorReference="anchorPosition"
      anchorPosition={{ top: menu.mouseY, left: menu.mouseX }}
    >
      <MenuItem onClick={handleCopy} dense>
        <ListItemIcon><ContentCopyIcon fontSize="small" /></ListItemIcon>
        <ListItemText>Copy cell</ListItemText>
      </MenuItem>
    </Menu>
  ) : null;

  return { onCellContextMenu, contextMenu };
}
