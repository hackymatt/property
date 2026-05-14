"use client";
import { useRef, useMemo, useState, useCallback } from "react";
import { Box, Button, Stack, Chip, Alert, useTheme } from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, IDatasource, IGetRowsParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import { useQueryClient } from "@tanstack/react-query";
import { useCellContextMenu } from "@/hooks/useCellContextMenu";
import AppLayout from "@/components/AppLayout";
import { runLogs } from "@/lib/api";
import type { JobRunLog, ExecutionStatus } from "@/lib/types";

const STATUS_COLOR: Record<ExecutionStatus, "default" | "warning" | "info" | "success" | "error"> = {
  pending: "warning",
  running: "info",
  success: "success",
  failed: "error",
  cancelled: "default",
};

const STAGE_COLOR: Record<string, "primary" | "secondary" | "info"> = {
  list_pages: "primary",
  list_items: "secondary",
  get_item: "info",
};

export default function RunLogPage() {
  const gridRef = useRef<AgGridReact<JobRunLog>>(null);
  const theme = useTheme();
  const gridTheme = theme.palette.mode === "dark" ? "ag-theme-quartz-dark" : "ag-theme-quartz";
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
        queryKey: ["run-logs", qp],
        queryFn: () => runLogs.list(qp).then((r) => r.data),
        staleTime: 10_000,
      })
        .then((data) => { params.successCallback(data.results, data.count); setErrorRef.current(""); })
        .catch(() => { params.failCallback(); setErrorRef.current("Failed to load run logs"); });
    },
  }), [queryClient]);

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["run-logs"] });
    gridRef.current?.api.refreshInfiniteCache();
  }, [queryClient]);

  const colDefs: ColDef<JobRunLog>[] = [
    {
      field: "created_at", headerName: "Time", width: 170, sortable: true, filter: true,
      valueFormatter: ({ value }) => new Date(value).toLocaleString(),
    },
    { field: "domain_name", headerName: "Domain", width: 130, filter: true, sortable: true },
    { field: "source", flex: 2, filter: true, sortable: true },
    {
      field: "stage", width: 120, filter: true,
      cellRenderer: ({ value }: { value: string }) => (
        <Chip label={value} color={STAGE_COLOR[value] ?? "default"} size="small" />
      ),
    },
    {
      field: "status", width: 110, filter: true, sortable: true,
      cellRenderer: ({ value }: { value: ExecutionStatus }) => (
        <Chip label={value} color={STATUS_COLOR[value] ?? "default"} size="small" />
      ),
    },
    { field: "url", flex: 3, filter: true },
    {
      field: "metadata", headerName: "Info", flex: 1, filter: true,
      valueFormatter: ({ value }) => {
        if (!value || !Object.keys(value).length) return "";
        return JSON.stringify(value);
      },
    },
  ];

  return (
    <AppLayout>
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
      <Stack direction="row" justifyContent="flex-end" mb={1}>
        <Button startIcon={<RefreshIcon />} onClick={refresh}>Refresh</Button>
      </Stack>
      <Box className={gridTheme} sx={{ height: "calc(100vh - 130px)" }}>
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
    </AppLayout>
  );
}
