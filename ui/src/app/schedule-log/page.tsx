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
import { scheduleLogs } from "@/lib/api";
import type { ScheduleRunLog, ExecutionStatus } from "@/lib/types";

const STATUS_COLOR: Record<ExecutionStatus, "default" | "warning" | "info" | "success" | "error"> = {
  pending: "warning",
  running: "info",
  success: "success",
  failed: "error",
  cancelled: "default",
};

export default function ScheduleLogPage() {
  const gridRef = useRef<AgGridReact<ScheduleRunLog>>(null);
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
        queryKey: ["schedule-logs", qp],
        queryFn: () => scheduleLogs.list(qp).then((r) => r.data),
        staleTime: 10_000,
      })
        .then((data) => { params.successCallback(data.results, data.count); setErrorRef.current(""); })
        .catch(() => { params.failCallback(); setErrorRef.current("Failed to load schedule logs"); });
    },
  }), [queryClient]);

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["schedule-logs"] });
    gridRef.current?.api.refreshInfiniteCache();
  }, [queryClient]);

  const colDefs: ColDef<ScheduleRunLog>[] = [
    {
      field: "created_at", headerName: "Time", width: 170, sortable: true, filter: true,
      valueFormatter: ({ value }) => new Date(value).toLocaleString(),
    },
    { field: "schedule_name", headerName: "Schedule", flex: 2, filter: true, sortable: true },
    {
      field: "status", width: 110, filter: true, sortable: true,
      cellRenderer: ({ value }: { value: ExecutionStatus }) => (
        <Chip label={value} color={STATUS_COLOR[value] ?? "default"} size="small" />
      ),
    },
    {
      field: "schedule_run_id", headerName: "Run ID", flex: 2, filter: true,
      valueFormatter: ({ value }) => value ?? "",
    },
    {
      field: "metadata", headerName: "Info", flex: 2, filter: true,
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
