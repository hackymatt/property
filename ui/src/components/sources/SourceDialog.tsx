"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Switch, FormControlLabel, Grid,
  MenuItem, Alert, Tab, Tabs, Box, Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { sources, domains } from "@/lib/api";
import type { ScraperSource } from "@/lib/types";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

interface Props {
  open: boolean;
  source: ScraperSource | null;
  onClose: () => void;
  onSave: () => void;
}

const DEFAULTS: Partial<ScraperSource> = {
  name: "", offer_url_prefix: "", is_active: true, notes: "",
  preamble_code: "", list_pages_code: "", list_items_code: "", get_item_code: "",
};

const CODE_TABS = [
  { label: "Preamble", key: "preamble_code" as const },
  { label: "List Pages", key: "list_pages_code" as const },
  { label: "List Items", key: "list_items_code" as const },
  { label: "Get Item", key: "get_item_code" as const },
];

export default function SourceDialog({ open, source, onClose, onSave }: Props) {
  const [form, setForm] = useState<Partial<ScraperSource>>(DEFAULTS);
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const { data: domainData } = useQuery({
    queryKey: ["domains", "all"],
    queryFn: () => domains.list({ limit: 10000 }).then((r) => r.data.results),
  });
  const domainList = domainData ?? [];

  useEffect(() => {
    setForm(source ?? DEFAULTS);
    setTab(0);
    setError("");
  }, [source, open]);

  const set = (k: keyof ScraperSource, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (source?.id) await sources.update(source.id, form);
      else await sources.create(form);
      onSave();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: unknown } })?.response?.data;
      setError(JSON.stringify(msg) ?? "Error saving");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth
      PaperProps={{ sx: { height: "90vh" } }}>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <DialogTitle>{source ? `Edit Source: ${source.name}` : "Add Scraper Source"}</DialogTitle>
        <DialogContent dividers sx={{ flex: 1, display: "flex", flexDirection: "column", gap: 2, overflow: "hidden" }}>
          {error && <Alert severity="error">{error}</Alert>}

          {/* Meta fields */}
          <Grid container spacing={2}>
            <Grid item xs={5}>
              <TextField label="Name" fullWidth required size="small"
                value={form.name ?? ""} onChange={(e) => set("name", e.target.value)}
                placeholder="otodom/sell/apartment/owner" />
            </Grid>
            <Grid item xs={3}>
              <TextField select label="Domain" fullWidth required size="small"
                value={form.domain ?? ""}
                onChange={(e) => set("domain", parseInt(e.target.value))}>
                {domainList.map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid item xs={3}>
              <TextField label="Offer URL Prefix" fullWidth size="small"
                value={form.offer_url_prefix ?? ""}
                onChange={(e) => set("offer_url_prefix", e.target.value)} />
            </Grid>
            <Grid item xs={1} display="flex" alignItems="center">
              <FormControlLabel
                control={<Switch size="small" checked={form.is_active ?? true}
                  onChange={(e) => set("is_active", e.target.checked)} />}
                label={<Typography variant="caption">Active</Typography>}
                labelPlacement="top"
                sx={{ m: 0 }}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField label="Notes" fullWidth size="small" multiline rows={1}
                value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value)} />
            </Grid>
          </Grid>

          {/* Code tabs */}
          <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable">
              {CODE_TABS.map((t, i) => <Tab key={t.key} label={t.label} value={i} />)}
            </Tabs>
            <Box sx={{ flex: 1, border: 1, borderColor: "divider", borderTop: 0 }}>
              {CODE_TABS.map((t, i) => (
                <Box key={t.key} hidden={tab !== i} height="100%">
                  {tab === i && (
                    <MonacoEditor
                      height="100%"
                      language="python"
                      value={form[t.key] ?? ""}
                      onChange={(v) => set(t.key, v ?? "")}
                      options={{
                        minimap: { enabled: false },
                        fontSize: 13,
                        tabSize: 4,
                        scrollBeyondLastLine: false,
                        wordWrap: "on",
                      }}
                    />
                  )}
                </Box>
              ))}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
