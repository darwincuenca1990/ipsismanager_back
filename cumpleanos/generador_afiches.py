from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from bailarines.google_drive import download_bailarin_photo


PLANTILLA_AFICHE = (
    Path(__file__).resolve().parent
    / 'assets'
    / 'plantilla_ipsis.jpeg'
)


def _cargar_fuente(tamano, negrita=False):
    fuentes = (
        [
            Path('C:/Windows/Fonts/arialbd.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ]
        if negrita
        else [
            Path('C:/Windows/Fonts/arial.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        ]
    )
    for fuente in fuentes:
        if fuente.is_file():
            return ImageFont.truetype(str(fuente), size=tamano)
    return ImageFont.load_default(size=tamano)


def _envolver_texto(texto, fuente, ancho_maximo):
    lineas = []
    linea = ''
    for palabra in texto.split():
        candidata = f'{linea} {palabra}'.strip()
        if fuente.getlength(candidata) <= ancho_maximo or not linea:
            linea = candidata
        else:
            lineas.append(linea)
            linea = palabra
    if linea:
        lineas.append(linea)
    return lineas


def _dibujar_texto_centrado(
    dibujo,
    texto,
    caja,
    tamano_maximo,
    tamano_minimo,
    negrita=False,
    color='white'
):
    izquierda, arriba, derecha, abajo = caja
    ancho = derecha - izquierda
    alto = abajo - arriba

    for tamano in range(tamano_maximo, tamano_minimo - 1, -2):
        fuente = _cargar_fuente(tamano, negrita=negrita)
        lineas = _envolver_texto(texto, fuente, ancho)
        alto_linea = dibujo.textbbox((0, 0), 'Ágj', font=fuente)[3]
        alto_texto = alto_linea * len(lineas)
        if alto_texto <= alto:
            break
    else:
        raise ValueError('El texto no cabe en el espacio del afiche.')

    y = arriba + (alto - alto_texto) / 2
    for linea in lineas:
        dibujo.text(
            (izquierda + ancho / 2, y),
            linea,
            fill=color,
            font=fuente,
            anchor='mt',
            stroke_width=1 if negrita else 0,
            stroke_fill='#5b1d1d'
        )
        y += alto_linea


def generar_afiche(bailarin, mensaje):
    if not PLANTILLA_AFICHE.is_file():
        raise FileNotFoundError(
            f'No se encontró la plantilla de afiche: {PLANTILLA_AFICHE}'
        )

    foto_drive = download_bailarin_photo(bailarin.fotografia_drive_id)
    try:
        plantilla = Image.open(PLANTILLA_AFICHE).convert('RGB')
        foto = Image.open(BytesIO(foto_drive['content'])).convert('RGB')
    except (OSError, ValueError) as error:
        raise ValueError(
            'No fue posible leer la plantilla o fotografía del bailarín.'
        ) from error

    ancho, alto = plantilla.size
    diametro = int(ancho * 0.37)
    foto = ImageOps.fit(
        foto,
        (diametro, diametro),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.4)
    )
    mascara = Image.new('L', (diametro, diametro), 0)
    ImageDraw.Draw(mascara).ellipse(
        (0, 0, diametro - 1, diametro - 1),
        fill=255
    )

    centro_x = int(ancho * 0.44)
    centro_y = int(alto * 0.57)
    posicion_foto = (
        centro_x - diametro // 2,
        centro_y - diametro // 2
    )
    plantilla.paste(foto, posicion_foto, mascara)
    ImageDraw.Draw(plantilla).ellipse(
        (
            posicion_foto[0] - 5,
            posicion_foto[1] - 5,
            posicion_foto[0] + diametro + 4,
            posicion_foto[1] + diametro + 4
        ),
        outline='#d9a441',
        width=max(4, ancho // 180)
    )

    dibujo = ImageDraw.Draw(plantilla)
    nombre = f'{bailarin.nombres} {bailarin.apellidos}'.strip()
    _dibujar_texto_centrado(
        dibujo,
        nombre,
        (
            int(ancho * 0.17),
            int(alto * 0.77),
            int(ancho * 0.75),
            int(alto * 0.86)
        ),
        tamano_maximo=int(ancho * 0.055),
        tamano_minimo=int(ancho * 0.025),
        negrita=True
    )

    caja_mensaje = (
        int(ancho * 0.09),
        int(alto * 0.895),
        int(ancho * 0.81),
        int(alto * 0.98)
    )
    dibujo.rounded_rectangle(
        caja_mensaje,
        radius=int(ancho * 0.025),
        fill=(91, 29, 30)
    )
    _dibujar_texto_centrado(
        dibujo,
        mensaje,
        (
            caja_mensaje[0] + int(ancho * 0.025),
            caja_mensaje[1] + int(alto * 0.01),
            caja_mensaje[2] - int(ancho * 0.025),
            caja_mensaje[3] - int(alto * 0.01)
        ),
        tamano_maximo=int(ancho * 0.032),
        tamano_minimo=int(ancho * 0.018)
    )

    salida = BytesIO()
    plantilla.save(salida, format='JPEG', quality=92, optimize=True)
    salida.seek(0)
    return salida.getvalue()
