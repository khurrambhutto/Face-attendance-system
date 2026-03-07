# Hugging Face Spaces Deployment

Use `scripts/prepare_hf_space.sh` to generate a deployable Docker Space folder from this repo.

## Generate the Space folder

```bash
./scripts/prepare_hf_space.sh /tmp/face-attendance-space
```

That output folder will contain:

- `app/`
- `models/`
- `requirements.txt`
- `Dockerfile`
- `README.md`

## Push to your Space

```bash
cd /tmp
git clone git@hf.co:spaces/khurrambhutto/face-attendance
rsync -av --delete /tmp/face-attendance-space/ /tmp/face-attendance/
cd /tmp/face-attendance
git add .
git commit -m "Deploy backend"
git push
```

## Required Space secrets

Add these in your Space settings:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_ANON_KEY`

Add these variables:

- `SUPABASE_BUCKET=enrollment-photos`
- `CORS_ORIGINS=https://khurrambhutto.github.io`

If your frontend uses a custom domain, replace `CORS_ORIGINS` with that origin.
