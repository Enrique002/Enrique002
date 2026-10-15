# Mantenimiento del perfil

Repositorio local: `C:\Users\Usuario\Projects\Enrique002`.  
El perfil de GitHub solo muestra este README si el repo se llama exactamente `Enrique002/Enrique002` y es público.

## Primera publicación (manual)

Este entorno no publica a GitHub. Cuando autorices el push:

```powershell
cd C:\Users\Usuario\Projects\Enrique002
git remote add origin https://github.com/Enrique002/Enrique002.git
git push -u origin main
```

Si el repositorio remoto aún no existe, créalo vacío en GitHub (sin README) y después haz el push.

## Retrato ASCII

No se usa una fotografía inventada ni la de otra persona. Hasta que envíes la tuya, `enrique-ascii.svg` es un monograma.

```powershell
# 1. Copia la foto a una ruta local (no se sube):
#    assets/photo.jpg
python scripts/prep_photo.py assets/photo.jpg
python scripts/make_ascii_svg.py
```

`assets/prepped.png` y `assets/photo.*` están en `.gitignore`.  
Opcional: `pip install rembg` para recortar el fondo con más precisión.

## Tarjeta Neofetch

Edita `data/info.json` y regenera:

```powershell
python scripts/make_info_card.py
```

## Mapa de calor

```powershell
python scripts/fetch_contributions.py
python scripts/render_heatmap_svg.py
```

Fuente pública (sin token): `https://github.com/users/Enrique002/contributions`.  
Si GitHub cambia el HTML, el script sale con error y **conserva** `data/contributions.json`. Fallback de pruebas: `--html-file captura.html`.

## GitHub Actions

Archivo: `.github/workflows/update-profile-art.yml`

- Cron actual: `0 6 * * *` (06:00 UTC). Cámbialo ahí si quieres otra hora.
- También se puede lanzar a mano en la pestaña Actions.
- No se dispara con `push`, así el commit del bot no entra en bucle.
- El mensaje incluye `[skip ci]` por si más adelante se añade otro disparador.
- Solo instala `scripts/requirements-heatmap.txt`.

## Validar

```powershell
python scripts/validate.py
```

## Limitaciones de GitHub

- Las animaciones SVG (SMIL) se reproducen al cargar la imagen; GitHub no ejecuta JavaScript en SVG.
- En móvil las dos columnas pueden apilarse o verse más estrechas.
- El calendario solo refleja contribuciones **públicas**.
