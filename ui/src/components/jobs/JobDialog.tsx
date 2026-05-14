"use client";
import { useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Switch, FormControlLabel, Grid,
  MenuItem, Alert,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { jobs, domains } from "@/lib/api";
import type { Job } from "@/lib/types";

interface Props {
  open: boolean;
  job: Job | null;
  onClose: () => void;
  onSave: () => void;
}

const STAGES = ["list_pages", "list_items", "get_item"];
const DEFAULTS: Partial<Job> = { name: "", source: "", stage: "list_pages", url: "", is_active: true };

export default function JobDialog({ open, job, onClose, onSave }: Props) {
  const [form, setForm] = useState<Partial<Job>>(DEFAULTS);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const { data: domainData } = useQuery({
    queryKey: ["domains", "all"],
    queryFn: () => domains.list({ limit: 10000 }).then((r) => r.data.results),
  });
  const domainList = domainData ?? [];

  useEffect(() => {
    setForm(job ?? DEFAULTS);
    setError("");
  }, [job, open]);

  const set = (k: keyof Job, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
              <TextField label="Name" fullWidth required placeholder="e.g. otodom-sell-apartments"
                value={form.name ?? ""} onChange={(e) => set("name", e.target.value)} />
            </Grid>
            <Grid item xs={12}>
              <TextField select label="Domain" fullWidth required value={form.domain ?? ""} onChange={(e) => set("domain", parseInt(e.target.value))}>
                {domainList.map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField label="Source" fullWidth required placeholder="otodom/sell/apartment/developer" value={form.source ?? ""} onChange={(e) => set("source", e.target.value)} />
            </Grid>
            <Grid item xs={6}>
              <TextField select label="Stage" fullWidth required value={form.stage ?? "list_pages"} onChange={(e) => set("stage", e.target.value)}>
                {STAGES.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
              </TextField>
            </Grid>
            <Grid item xs={6} display="flex" alignItems="center">
              <FormControlLabel control={<Switch checked={form.is_active ?? true} onChange={(e) => set("is_active", e.target.checked)} />} label="Active" />
            </Grid>
            <Grid item xs={12}>
              <TextField label="URL" fullWidth required value={form.url ?? ""} onChange={(e) => set("url", e.target.value)} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
