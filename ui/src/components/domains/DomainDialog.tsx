"use client";
import { useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Switch, FormControlLabel, Grid, Alert,
} from "@mui/material";
import { domains } from "@/lib/api";
import type { Domain } from "@/lib/types";

interface Props {
  open: boolean;
  domain: Domain | null;
  onClose: () => void;
  onSave: () => void;
}

const DEFAULTS: Partial<Domain> = {
  name: "", is_active: true, requests_per_second: 1.0,
  burst_capacity: 2, concurrent_requests: 1, max_retries: 3,
  retry_delay: 5.0, notes: "",
};

export default function DomainDialog({ open, domain, onClose, onSave }: Props) {
  const [form, setForm] = useState<Partial<Domain>>(DEFAULTS);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(domain ?? DEFAULTS);
    setError("");
  }, [domain, open]);

  const set = (k: keyof Domain, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (domain?.id) await domains.update(domain.id, form);
      else await domains.create(form);
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
        <DialogTitle>{domain ? "Edit Domain" : "Add Domain"}</DialogTitle>
        <DialogContent dividers>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField label="Name" fullWidth required value={form.name ?? ""} onChange={(e) => set("name", e.target.value)} />
            </Grid>
            <Grid item xs={6}>
              <TextField label="Requests / second" type="number" fullWidth inputProps={{ step: 0.1 }} value={form.requests_per_second ?? 1} onChange={(e) => set("requests_per_second", parseFloat(e.target.value))} />
            </Grid>
            <Grid item xs={6}>
              <TextField label="Burst capacity" type="number" fullWidth value={form.burst_capacity ?? 2} onChange={(e) => set("burst_capacity", parseInt(e.target.value))} />
            </Grid>
            <Grid item xs={6}>
              <TextField label="Concurrent requests" type="number" fullWidth value={form.concurrent_requests ?? 1} onChange={(e) => set("concurrent_requests", parseInt(e.target.value))} />
            </Grid>
            <Grid item xs={6}>
              <TextField label="Max retries" type="number" fullWidth value={form.max_retries ?? 3} onChange={(e) => set("max_retries", parseInt(e.target.value))} />
            </Grid>
            <Grid item xs={6}>
              <TextField label="Retry delay (s)" type="number" fullWidth inputProps={{ step: 0.5 }} value={form.retry_delay ?? 5} onChange={(e) => set("retry_delay", parseFloat(e.target.value))} />
            </Grid>
            <Grid item xs={6} display="flex" alignItems="center">
              <FormControlLabel control={<Switch checked={form.is_active ?? true} onChange={(e) => set("is_active", e.target.checked)} />} label="Active" />
            </Grid>
            <Grid item xs={12}>
              <TextField label="Notes" fullWidth multiline rows={2} value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value)} />
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
