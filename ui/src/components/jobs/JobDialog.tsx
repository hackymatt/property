"use client";
import { useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Switch, FormControlLabel, Grid,
  MenuItem, Alert, Autocomplete,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { jobs, domains, sources } from "@/lib/api";
import type { Job, ScraperSource } from "@/lib/types";

interface Props {
  open: boolean;
  job: Job | null;
  onClose: () => void;
  onSave: () => void;
}

const DEFAULTS: Partial<Job> = { name: "", source: "", stage: "", url: "", params: {}, is_active: true };

export default function JobDialog({ open, job, onClose, onSave }: Props) {
  const [form, setForm] = useState<Partial<Job>>(DEFAULTS);
  const [paramsText, setParamsText] = useState("{}");
  const [paramsError, setParamsError] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const { data: domainData } = useQuery({
    queryKey: ["domains", "all"],
    queryFn: () => domains.list({ limit: 10000 }).then((r) => r.data.results),
  });
  const domainList = domainData ?? [];

  const { data: sourceData } = useQuery({
    queryKey: ["sources", "all"],
    queryFn: () => sources.list({ limit: 10000 }).then((r) => r.data.results),
  });
  const allSources = sourceData ?? [];

  // Filter sources by selected domain
  const filteredSources = form.domain
    ? allSources.filter((s) => s.domain === form.domain)
    : allSources;

  const selectedSource = allSources.find((s) => s.name === form.source) ?? null;

  // Stage options come from the selected source's own pipeline — the
  // vocabulary differs per source_kind (portal vs file registry), so a
  // hardcoded list would be wrong for anything but Otodom.
  const stageOptions = [...(selectedSource?.stages ?? [])]
    .sort((a, b) => a.order - b.order)
    .map((s) => s.stage_name);

  useEffect(() => {
    setForm(job ?? DEFAULTS);
    setParamsText(JSON.stringify(job?.params ?? {}, null, 2));
    setParamsError("");
    setError("");
  }, [job, open]);

  const set = (k: keyof Job, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const handleParamsChange = (text: string) => {
    setParamsText(text);
    try {
      const parsed = text.trim() === "" ? {} : JSON.parse(text);
      set("params", parsed);
      setParamsError("");
    } catch {
      setParamsError("Invalid JSON");
    }
  };

  // When domain changes, clear source if it no longer belongs to the new domain
  const handleDomainChange = (domainId: number) => {
    set("domain", domainId);
    const currentSource = allSources.find((s) => s.name === form.source);
    if (currentSource && currentSource.domain !== domainId) {
      set("source", "");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (paramsError) {
      setError("Fix the params JSON before saving");
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (job?.id) await jobs.update(job.id, form);
      else await jobs.create(form);
      onSave();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: unknown } })?.response?.data;
      setError(JSON.stringify(msg) ?? "Error saving");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>{job ? "Edit Job" : "Add Job"}</DialogTitle>
        <DialogContent dividers>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                label="Name" fullWidth placeholder="e.g. otodom-sell-apartments"
                value={form.name ?? ""}
                onChange={(e) => set("name", e.target.value)}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                select label="Domain" fullWidth required
                value={form.domain ?? ""}
                onChange={(e) => handleDomainChange(parseInt(e.target.value))}
              >
                {domainList.map((d) => (
                  <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <Autocomplete<ScraperSource>
                options={filteredSources}
                value={selectedSource}
                getOptionLabel={(s) => s.name}
                onChange={(_, val) => set("source", val?.name ?? "")}
                noOptionsText={
                  form.domain
                    ? "No active sources for this domain"
                    : "Select a domain first"
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Source"
                    required
                    placeholder="Select a scraper source"
                  />
                )}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                select label="Stage" fullWidth required
                value={stageOptions.includes(form.stage ?? "") ? form.stage : ""}
                onChange={(e) => set("stage", e.target.value)}
                disabled={!selectedSource}
                helperText={
                  !selectedSource
                    ? "Select a source first"
                    : stageOptions.length === 0
                      ? "This source has no stages defined"
                      : "Usually the first stage"
                }
              >
                {stageOptions.map((s, i) => (
                  <MenuItem key={s} value={s}>{i + 1}. {s}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={6} display="flex" alignItems="center">
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_active ?? true}
                    onChange={(e) => set("is_active", e.target.checked)}
                  />
                }
                label="Active"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="URL" fullWidth required
                value={form.url ?? ""}
                onChange={(e) => set("url", e.target.value)}
                helperText={
                  selectedSource?.source_kind === "FILE_REGISTRY"
                    ? "Not fetched for file-registry sources — scope comes from Params below. Kept as a reference/base URL."
                    : "Starting URL for the first stage (e.g. a search results page)"
                }
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Params (JSON)" fullWidth multiline minRows={3}
                value={paramsText}
                onChange={(e) => handleParamsChange(e.target.value)}
                error={!!paramsError}
                helperText={
                  paramsError ||
                  (selectedSource?.source_kind === "FILE_REGISTRY"
                    ? 'RCN scope — one county: {"teryt_codes": ["1261"]} · all: {"teryt_codes": "all"}'
                    : "Usually {} for portal sources — the scope is the URL")
                }
                InputProps={{ style: { fontFamily: "monospace", fontSize: 13 } }}
              />
            </Grid>
          </Grid>
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
