"use client";
import { useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Switch, FormControlLabel, Grid,
  Autocomplete, Alert, Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { schedules, jobs } from "@/lib/api";
import type { Schedule, Job } from "@/lib/types";

interface Props {
  open: boolean;
  schedule: Schedule | null;
  onClose: () => void;
  onSave: () => void;
}

const DEFAULTS: Partial<Schedule> = { name: "", cron: "0 6 * * *", jobs: [], is_active: true };

export default function ScheduleDialog({ open, schedule, onClose, onSave }: Props) {
  const [form, setForm] = useState<Partial<Schedule>>(DEFAULTS);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const { data: jobData } = useQuery({
    queryKey: ["jobs", "all"],
    queryFn: () => jobs.list({ limit: 10000 }).then((r) => r.data.results),
  });
  const jobList = jobData ?? [];

  useEffect(() => {
    setForm(schedule ?? DEFAULTS);
    setError("");
  }, [schedule, open]);

  const set = (k: keyof Schedule, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const selectedJobs = jobList.filter((j) => (form.jobs as number[] ?? []).includes(j.id));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (schedule?.id) await schedules.update(schedule.id, form);
      else await schedules.create(form);
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
        <DialogTitle>{schedule ? "Edit Schedule" : "Add Schedule"}</DialogTitle>
        <DialogContent dividers>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField label="Name" fullWidth required value={form.name ?? ""} onChange={(e) => set("name", e.target.value)} />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Cron expression"
                fullWidth required
                value={form.cron ?? ""}
                onChange={(e) => set("cron", e.target.value)}
                helperText="e.g. 0 6 * * * (daily at 6am)"
              />
            </Grid>
            <Grid item xs={12}>
              <Autocomplete
                multiple
                options={jobList}
                value={selectedJobs}
                getOptionLabel={(j) => j.name || `${j.source} [${j.stage}]`}
                onChange={(_, val) => set("jobs", val.map((j) => j.id))}
                renderInput={(params) => <TextField {...params} label="Jobs" placeholder="Select jobs…" />}
              />
            </Grid>
            <Grid item xs={6} display="flex" alignItems="center">
              <FormControlLabel control={<Switch checked={form.is_active ?? true} onChange={(e) => set("is_active", e.target.checked)} />} label="Active" />
            </Grid>
            {schedule?.next_run && (
              <Grid item xs={12}>
                <Typography variant="caption" color="text.secondary">
                  Next run: {new Date(schedule.next_run).toLocaleString()}
                </Typography>
              </Grid>
            )}
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
