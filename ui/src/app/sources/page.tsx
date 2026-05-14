"use client";
import { useRef, useMemo, useState, useCallback } from "react";
import { Box, Button, Stack, Chip, Alert, useTheme } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, IDatasource, IGetRowsParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import { useQueryClient } from "@tanstack/react-query";
import { useCellContextMenu } from "@/hooks/useCellContextMenu";
import AppLayout from "@/components/AppLayout";
import SourceDialog from "@/components/sources/SourceDialog";
import ConfirmDialog from "@/components/ConfirmDialog";
import { sources } from "@/lib/api";
import type { ScraperSource } from "@/lib/types";

export default function SourcesPage() {
  const gridRef = useRef<AgGridReact<ScraperSource>>(null);
  const theme = useTheme();
  const gridTheme = theme.palette.mode === "dark" ? "ag-theme-quartz-dark" : "ag-theme-quartz";
  const [selected, setSelected] = useState<ScraperSource | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ScraperSource | null>(null);
  const [error, setError] = useState("");
  const setErrorRef = useRef(setError);
  setErrorRef.current = setError;

  const queryClient = useQueryClient();
  const { onCellContextMenu, contextMenu } = useCellContextMenu();

  const datasource = useMemo<IDatasource>(() => ({
    getRows(params: IGetRowsParams) {
      const limit = params.endRow - params.startRow;
      const offset = params.startRow;
      const search = Object.values(params.filterModel ?? {})
        .map((f) => (f as { filter?: string }).filter).filter(Boolean).join(" ");
      const ordering = params.sortModel
        .map((s) => `${s.sort === "desc" ? "-" : ""}${s.colId}`).join(",");
      const qp: Record<string, string | number> = { limit, offset };
      if (search) qp.search = search;
      if (ordering) qp.ordering = ordering;

      queryClient.fetchQuery({
        queryKey: ["sources", qp],
        queryFn: () => sources.list(qp).then((r) => r.data),
        staleTime: 30_000,
      })
        .then((data) => { params.successCallback(data.results, data.count); setErrorRef.current(""); })
        .catch(() => { params.failCallback(); setErrorRef.current("Failed to load sources"); });
    },
  }), [queryClient]);

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["sources"] });
    gridRef.current?.api.refreshInfiniteCache();
  }, [queryClient]);

  const handleSave = () => { refresh(); setDialogOpen(false); setSelected(null); };
  const handleDelete = async () => {
    if (!deleteTarget) return;
    await sources.remove(deleteTarget.id);
    setDeleteTarget(null);
    refresh();
  };

  const colDefs: ColDef<ScraperSource>[] = [
    { field: "name", flex: 3, filter: true, sortable: true },
    { field: "domain_name", headerName: "Domain", flex: 1, filter: true, sortable: true },
    {
      field: "is_active", headerName: "Active", width: 100, filter: true,
      cellRenderer: ({ value }: { value: boolean }) => (
        <Chip label={value ? "Yes" : "No"} color={value ? "success" : "default"} size="small" />
      ),
    },
    { field: "offer_url_prefix", headerName: "Offer URL Prefix", flex: 2, filter: true },
    {
      headerName: "Actions", width: 160, sortable: false, filter: false,
      cellRenderer: ({ data }: { data: ScraperSource }) => (
        <Stack direction="row" spacing={1} alignItems="center" height="100%">
          <Button size="small" onClick={() => { setSelected(data); setDialogOpen(true); }}>Edit</Button>
          <Button size="small" color="error" onClick={() => setDeleteTarget(data)}>Delete</Button>
        </Stack>
      ),
    },
  ];

  return (
    <AppLayout>
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
      <Stack direction="row" justifyContent="flex-end" mb={1}>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => { setSelected(null); setDialogOpen(true); }}>
          Add Source
        </Button>
      </Stack>
      <Box className={gridTheme} sx={{ height: "calc(100vh - 140px)" }}>
        <AgGridReact
          ref={gridRef}
          rowModelType="infinite"
          datasource={datasource}
          cacheBlockSize={100}
          columnDefs={colDefs}
          rowHeight={42}
          defaultColDef={{ floatingFilter: true }}
          preventDefaultOnContextMenu
          onCellContextMenu={onCellContextMenu}
        />
      </Box>
      {contextMenu}
      <SourceDialog open={dialogOpen} source={selected} onClose={() => { setDialogOpen(false); setSelected(null); }} onSave={handleSave} />
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Source"
        message={`Delete "${deleteTarget?.name}"?`}
        onConfirm={handleDelete}
        onClose={() => setDeleteTarget(null)}
      />
    </AppLayout>
  );
}
