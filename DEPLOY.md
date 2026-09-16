# Deploying menu3d

Two backend paths are documented below - pick one:

- **Option A: Render (free tier) + Vercel** - fastest to set up, no server to
  manage, good for getting a real URL live quickly.
- **Option B: VPS (Docker + Caddy) + Vercel** - `docker-compose.yml` and
  `Caddyfile` in this repo are built for this; use it once you need more than
  Render's free tier gives you (it sleeps after 15 min idle, wakes up slowly).

Both options deploy the three frontends (`admin`, `super-admin`, `customer`)
to Vercel as three separate projects.

## Option A: Render + Vercel

### A.1 Database

Render's free plan doesn't include Postgres, so use a free external one -
[Neon](https://neon.tech) or [Supabase](https://supabase.com) both work.
Create a project, copy its Postgres connection string (`postgres://...`) -
that's your `DATABASE_URL`.

### A.2 Backend (Render)

New → Web Service → connect this repo:

- **Root Directory**: `backend`
- **Environment**: Docker (it will find `backend/Dockerfile`)
- **Instance Type**: Free
- **Health Check Path**: `/health/`

Environment variables (Render dashboard → Environment, not a file):

| Key | Value |
|---|---|
| `SECRET_KEY` | generate: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `<your-service-name>.onrender.com` (pick the service name up front so you know this before deploying) |
| `DATABASE_URL` | the Neon/Supabase connection string from A.1 |
| `CORS_ALLOWED_ORIGINS` | the 3 Vercel URLs from A.3, comma-separated, no trailing slash |
| `FRONTEND_BASE_URL` | the customer app's Vercel URL (baked into every table's QR code) |
| `CLOUDFLARE_ACCOUNT_ID` | from your Cloudflare R2 dashboard |
| `CLOUDFLARE_ACCESS_KEY_ID` | R2 API token |
| `CLOUDFLARE_SECRET_ACCESS_KEY` | R2 API token |
| `CLOUDFLARE_R2_BUCKET` | R2 bucket name |
| `CLOUDFLARE_R2_PUBLIC_URL` | R2 bucket's public URL |
| `AISTUDIO_TOKEN` | 3daistudio.com API token |
| `WEB_CONCURRENCY` | `2` (free tier has 512MB RAM - the default of 3 gunicorn workers can OOM it) |

Do **not** set `PORT` - Render injects it itself and `entrypoint.sh` already
binds to it (`${PORT:-8000}`).

Media uploads (`CLOUDFLARE_*`) are required here even for testing - Render's
filesystem is ephemeral, so without R2 every uploaded image disappears on the
next deploy or restart.

Deploy, then open a shell (Render dashboard → Shell) and run:

```bash
python manage.py createsuperuser
```

Migrations and `collectstatic` already ran automatically on boot
(`backend/entrypoint.sh`). Re-deploys are automatic on every push to `main`
by default.

### A.3 Frontends (Vercel)

Create three separate Vercel projects from this repo, one per app, each with
its **Root Directory** set accordingly:

| Vercel project | Root Directory |
|---|---|
| menu3d-admin | `frontend/admin` |
| menu3d-super-admin | `frontend/super-admin` |
| menu3d-customer | `frontend/customer` |

Same single environment variable on all three:

```
NEXT_PUBLIC_API_URL=https://<your-service-name>.onrender.com
```

This is inlined at build time, so redeploy on Vercel after changing it.

Once you have the three `*.vercel.app` URLs, go back to Render's
`CORS_ALLOWED_ORIGINS` and set those exact origins, then redeploy the
backend - cookie auth will 401 silently otherwise (blocked by CORS, not a
login bug).

### A.4 First-time checks

- `https://<your-service-name>.onrender.com/health/` returns `{"status": "ok"}`.
- First request after idle takes ~30-60s on the free tier (cold start) -
  expected, not a bug.
- Log into the admin app; if it hangs on "loading", check the browser's
  network tab for CORS errors first (see A.3's last paragraph).
- Render dashboard → Logs for gunicorn/Django errors.

## Option B: VPS (Docker + Caddy) + Vercel

Requirements: a VPS with Docker + the Docker Compose plugin installed, and a
domain (e.g. `api.yourdomain.com`) with its DNS A record pointed at the VPS's
IP - Caddy needs that to work before it can issue a certificate.

```bash
git clone <this repo> menu3d && cd menu3d

# Root env (Caddy + Postgres)
cp .env.example .env
# edit .env: set DOMAIN and a real POSTGRES_PASSWORD

# Backend env (Django)
cp backend/.env.example backend/.env
# edit backend/.env - required:
#   SECRET_KEY            (generate: python -c "import secrets; print(secrets.token_urlsafe(50))")
#   DEBUG=False
#   ALLOWED_HOSTS          e.g. api.yourdomain.com
#   CORS_ALLOWED_ORIGINS   the 3 Vercel URLs, comma-separated, no trailing slash
#   FRONTEND_BASE_URL      the customer app's URL (baked into every table's QR code)
#   CLOUDFLARE_*           R2 bucket for uploaded images (required whenever DEBUG=False)
#   AISTUDIO_TOKEN         3daistudio.com API token
# DATABASE_URL is set for you by docker-compose.yml - leave it blank here.

docker compose up -d --build
docker compose exec backend python manage.py createsuperuser
```

Migrations and `collectstatic` run automatically on container start
(`backend/entrypoint.sh`). The API is now live at `https://<DOMAIN>/`.

Redeploying after a code change:

```bash
git pull
docker compose up -d --build backend
```

Note: `backend` isn't published to the host — only Caddy (ports 80/443) is.
That's what makes it safe for gunicorn to speak plain HTTP internally.

Frontends: same as Option A.3, but `NEXT_PUBLIC_API_URL=https://<DOMAIN>`.

First-time checks: same as A.4, but `docker compose logs -f backend` /
`docker compose logs -f caddy` instead of the Render dashboard (check Caddy's
logs if the certificate isn't issuing - usually a DNS or port 80/443
firewall issue).

## iOS AR (USDZ conversion via Blender)

`backend/Dockerfile` installs Blender (`apt-get install blender`, run
headlessly - no display/GPU needed) and sets `BLENDER_BINARY` for you, so
this needs **no extra setup** on either Option A or B - both build from
this same Dockerfile. Whenever a food's 3D model finishes generating, the
backend automatically converts its (already size-normalized) GLB to USDZ
for iOS Quick Look; Android and web only ever need the GLB and are
unaffected if USDZ conversion fails for any reason.

Caveats:

- **Render free tier (512MB RAM)**: Blender's own memory use on top of
  gunicorn can be tight on the free instance, especially with concurrent
  requests. If iOS AR matters, use a paid Render instance type with more
  RAM, or the VPS path (Option B), which typically has more headroom.
- **First deploy after this feature ships**: existing foods created before
  Blender was wired in won't have a USDZ yet (or have one baked at the old,
  pre-normalization size). Run once after deploying:

  ```bash
  # VPS
  docker compose exec backend python manage.py normalize_models
  # Render: same command from the dashboard's Shell tab
  ```

  Safe to re-run any time - it never touches a working file in place, and
  skips GLBs that are already normalized.
- Admin's food list shows a separate "iOS:" status (tayyor / navbatda /
  xatolik) next to the GLB one, so a stuck USDZ conversion never looks like
  the whole model failed - Android/web keep working either way.

## Custom domains (either option)

Vercel and Render/the VPS all accept a custom domain instead of their default
`*.vercel.app` / `*.onrender.com` one. A clean structure for this project:

| Domain | Points to |
|---|---|
| `menu.yourdomain.com` | Customer app (`frontend/customer`) - the one on every QR code |
| `admin.yourdomain.com` | Admin app (`frontend/admin`) |
| `superadmin.yourdomain.com` | Super-admin app (`frontend/super-admin`) |
| `api.yourdomain.com` | Django backend |

Add each frontend's domain in its Vercel project's Settings -> Domains (Vercel
gives you the DNS record to add). Point `api.yourdomain.com` at the VPS
(`DOMAIN` in the root `.env`) or add it as a custom domain in Render.

Whenever you attach or change the customer app's domain, update
`FRONTEND_BASE_URL` on the backend to match, redeploy the backend, then
re-render existing QR codes against the new domain (table tokens are
untouched - only the PNG's encoded URL changes):

```bash
# VPS
docker compose exec backend python manage.py regenerate_qr_codes
# Render: run the same command from the dashboard's Shell tab
```

Also update `CORS_ALLOWED_ORIGINS` on the backend to the three custom
frontend domains (not the `*.vercel.app` ones) once they're attached.

## QR va mobil AR: production uchun majburiy tekshiruv

QR menyu `FRONTEND_BASE_URL/menu/<table-token>` manziliga olib boradi. Shu
sababli QR kodi, customer frontend, API va media fayllar uchun hammasi HTTPS
orqali ishlashi kerak. `localhost`, IP-manzil yoki HTTP manzil bilan chiqarilgan
QR kodni restorandagi mehmon telefonida ishlatish mumkin emas.

### 1. Domenlarni yakunlab, so'ng QR kodlarni yangilang

Avval customer ilovasi uchun yakuniy HTTPS manzilni belgilang, masalan
`https://menu.yourdomain.com`. Backendda aynan shu qiymatni qo'ying:

```env
FRONTEND_BASE_URL=https://menu.yourdomain.com
CORS_ALLOWED_ORIGINS=https://menu.yourdomain.com,https://admin.yourdomain.com,https://superadmin.yourdomain.com
```

So'ng backendni qayta deploy qiling va mavjud QR rasmlarini qayta yarating:

```bash
# VPS
docker compose exec backend python manage.py regenerate_qr_codes

# Render Shell
python manage.py regenerate_qr_codes
```

Har bir stol uchun admin paneldan QR ni yuklab olib, oddiy telefon kamerasi
bilan tekshiring: u `https://menu.../menu/<token>` ga ochilishi va stolning
faol menyusini ko'rsatishi kerak. Domenni keyin o'zgartirsangiz, shu buyruqni
yana ishga tushiring.

### 2. Cloudflare R2: 3D fayllar uchun CORS va Content-Type

Productionda rasmlar hamda `.glb` / `.usdz` fayllar R2 dan keladi. R2 bucket
uchun public custom domain (masalan, `https://media.yourdomain.com`) ulang va
`CLOUDFLARE_R2_PUBLIC_URL` ga shu HTTPS manzilni yozing. Customer originini
R2 bucket CORS sozlamasiga qo'shing:

```json
[
  {
    "AllowedOrigins": ["https://menu.yourdomain.com"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": [],
    "ExposeHeaders": ["Content-Length", "Content-Type", "Accept-Ranges"],
    "MaxAgeSeconds": 3600
  }
]
```

`menu.yourdomain.com` ni haqiqiy customer domeningiz bilan almashtiring.
Bir nechta customer domeni (masalan, vaqtincha Vercel domeni) bo'lsa, har
birini `AllowedOrigins` ro'yxatiga alohida qo'shing. R2 CORS siyosati aniq
origin, metod va headerlar bilan beriladi; siyosat yangilangach, CDN cache
ta'sir qilsa Cloudflare cache'ni purge qiling. [Cloudflare R2 CORS
qo'llanmasi](https://developers.cloudflare.com/r2/buckets/cors/).

Deploydan keyin kamida bitta haqiqiy model URL'i uchun quyidagilarni
tekshiring (brauzer yoki `curl -I` orqali):

| Fayl | Kutiladigan `Content-Type` |
|---|---|
| `.glb` | `model/gltf-binary` |
| `.usdz` | `model/vnd.usdz+zip` |

Bu loyiha upload vaqtida ushbu MIME turlarini sozlaydi. R2 yoki proxy ularni
`application/octet-stream` qilib yuborsa, AR tugmasi ayrim iPhone yoki Android
qurilmalarda ishlamasligi mumkin.

### 3. iOS va Android qurilma talablari

- **iPhone/iPad:** QR ni Safari yoki telefonning standart kamerasi orqali
  oching. AR uchun qurilma ARKit/Quick Look'ni qo'llashi va taomda `USDZ`
  fayli tayyor bo'lishi kerak. Admin menyu sahifasidagi `iOS: tayyor` holatini
  tekshiring. Telegram/Instagram kabi ichki brauzer AR ni cheklashi mumkin;
  bunday holda foydalanuvchi "Safari'da ochish"ni tanlaydi.
- **Android:** Google Chrome hamda Google Play Services for AR (ARCore)
  yangilangan bo'lishi kerak. GLB fayl tayyor bo'lsa, `Stol ustida ko'rish`
  tugmasi Scene Viewer orqali ochiladi.
- Har ikkisi uchun model va customer sahifasi public HTTPS manzilda bo'lishi
  shart. Ichki tarmoqdagi `http://192.168...` yoki development URL production
  AR uchun mos emas.

### 4. Go-live oldidan AR test ro'yxati

1. `python manage.py normalize_models` ni bir marta ishga tushiring; avvalgi
   taom modellari ham real stol o'lchamiga yaqinlashtiriladi va iOS uchun USDZ
   tayyorlanadi.
2. Admin panelda sinov taomi uchun GLB **va** `iOS: tayyor` statusini ko'ring.
3. Restorandagi haqiqiy QR rasmni iPhone va Android telefon bilan alohida
   skanerlab ko'ring.
4. Menyu ochilgach taomni bosing, 3D preview yuklanganini tekshiring va
   `Stol ustida ko'rish` tugmasini bosing. Kamera ruxsatini bering va model
   stol ustiga joylashishini sinang.
5. Shu QR dan taomni savatga qo'shib, naqd, karta va onlayn to'lov usullarini
   ko'ring; test buyurtmasi admin `Buyurtmalar` sahifasida chiqishini tekshiring.

Render free instance uyquga ketishi va Blender USDZ conversion uchun xotirasi
kamligi sababli, restoran ishga tushishi hamda iOS AR muhim bo'lsa, VPS yoki
yetarli xotirali pullik Render instance tanlang.
