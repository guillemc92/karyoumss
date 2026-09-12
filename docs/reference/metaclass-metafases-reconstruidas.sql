/* ===========================================================================
   3 metafases reconstruidas sobre el esquema real de MetaClass (script.sql)
   ---------------------------------------------------------------------------
   script.sql es SOLO esquema (48 tablas, 0 INSERT). Estas 3 metafases se
   reconstruyen FIELES a la estructura legada, anonimizadas (RN-03, sin PII
   real: NHC = código CHN, nombres = ANON) y clínicamente coherentes.

   Cadena legada MetaClass:
     SCAPersona (paciente)
       -> SCAMuestra (muestra)
            -> SCAAnalisisCariotipos (LA METAFASE: ImagenMetafase + comentarios
               + su cariotipo ImagenCariotipo)
            -> SCAContador (nº de metafases contadas)
            -> SCACromosomas (cromosomas del análisis)
     SCADiagnosticName (catálogo de diagnósticos)

   Las columnas [image] (ImagenMetafase/ImagenCariotipo/ImagenCromosoma) son
   blobs binarios de microscopio: NO reconstruibles a partir del esquema, van
   NULL (el dato clínico va en los comentarios / ISCN).

   Mapeo al stack nuevo (backend-clinic, ADR-0015/0016/0021):
     SCAPersona            -> PatientVault (cifrada)      | SCAMuestra   -> Sample
     SCAAnalisisCariotipos -> Karyotype + SampleImage     | SCACromosomas-> Chromosome
     ComentariosCariotipo/ISCN -> iscn_nomenclature (RN-04, ADR-0023 S3)
   =========================================================================== */

SET IDENTITY_INSERT SCADiagnosticName ON;
INSERT INTO SCADiagnosticName (DiagId, DiagName, Flag) VALUES
    (1, N'Cariotipo normal',           1),
    (2, N'Síndrome de Down (+21)',     1),
    (3, N'Síndrome de Klinefelter',    1);
SET IDENTITY_INSERT SCADiagnosticName OFF;

/* --- Pacientes (anonimizados: NHC = CHN, nombre = ANON) --------------------- */
SET IDENTITY_INSERT SCAPersona ON;
INSERT INTO SCAPersona (IdPersona, Tipo, Referencia, Nombre, Apellido1, Apellido2, NHC, Alta) VALUES
    (101, 1, N'CHN-2026-07-24-0101', N'ANON', N'ANON', N'ANON', N'CHN-2026-07-24-0101', '2026-07-24'),
    (102, 1, N'CHN-2026-07-24-0102', N'ANON', N'ANON', N'ANON', N'CHN-2026-07-24-0102', '2026-07-24'),
    (103, 1, N'CHN-2026-07-24-0103', N'ANON', N'ANON', N'ANON', N'CHN-2026-07-24-0103', '2026-07-24');
SET IDENTITY_INSERT SCAPersona OFF;

/* --- Muestras (sangre periférica, cultivo linfocitario) --------------------- */
SET IDENTITY_INSERT SCAMuestra ON;
INSERT INTO SCAMuestra (IdMuestra, IdPersona, IdEspecie, IdCentro, IdDoctor, Referencia, FechaAnalisis, FechaObtencion, Observaciones, Diagnostic, Method) VALUES
    (201, 101, 1, 1, 1, N'CHN-2026-07-24-0101', '2026-07-24', '2026-07-22', N'Sangre periférica, cultivo linfocitario 72h, bandeo GTG 450-550 bandas', N'Cariotipo normal',        N'Bandeo GTG'),
    (202, 102, 1, 1, 1, N'CHN-2026-07-24-0102', '2026-07-24', '2026-07-22', N'Sangre periférica, cultivo linfocitario 72h, bandeo GTG 450-550 bandas', N'Síndrome de Down (+21)',  N'Bandeo GTG'),
    (203, 103, 1, 1, 1, N'CHN-2026-07-24-0103', '2026-07-24', '2026-07-22', N'Sangre periférica, cultivo linfocitario 72h, bandeo GTG 450-550 bandas', N'Síndrome de Klinefelter', N'Bandeo GTG');
SET IDENTITY_INSERT SCAMuestra OFF;

/* --- LAS 3 METAFASES (SCAAnalisisCariotipos) -------------------------------- */
/* ImageX/ImageY = dimensiones en px de la imagen de metafase capturada.       */
SET IDENTITY_INSERT SCAAnalisisCariotipos ON;
INSERT INTO SCAAnalisisCariotipos
    (IdAnalisis, IdMuestra, Referencia, ImagenMetafase, ComentariosMetafase, ImagenCariotipo, ComentariosCariotipo, Fecha, Observaciones, ImageX, ImageY, ImageCarioX, ImageCarioY)
VALUES
    -- Metafase 1: normal femenino 46,XX
    (301, 201, N'M1', NULL,
        N'Metafase bien extendida, 46 cromosomas, sin solapamientos ni pérdidas; calidad alta.',
        NULL, N'46,XX',
        '2026-07-24', N'Cariograma normal femenino. Confianza IA media 96%.',
        1600, 1200, 1024, 768),
    -- Metafase 2: trisomía 21 masculino 47,XY,+21
    (302, 202, N'M1', NULL,
        N'Metafase con 47 cromosomas; tres copias claras del par 21 (trisomía). Buena separación.',
        NULL, N'47,XY,+21',
        '2026-07-24', N'Trisomía 21 libre (Síndrome de Down). Par 21 marcado por el analista.',
        1600, 1200, 1024, 768),
    -- Metafase 3: Klinefelter 47,XXY (relevante en andrología)
    (303, 203, N'M1', NULL,
        N'Metafase con 47 cromosomas; complemento sexual XXY (dos X + una Y).',
        NULL, N'47,XXY',
        '2026-07-24', N'Síndrome de Klinefelter. Hallazgo en estudio de infertilidad masculina.',
        1600, 1200, 1024, 768);
SET IDENTITY_INSERT SCAAnalisisCariotipos OFF;

/* --- Contador de metafases revisadas por muestra ---------------------------- */
SET IDENTITY_INSERT SCAContador ON;
INSERT INTO SCAContador (IdContador, IdMuestra, Referencia, TotalContadas) VALUES
    (401, 201, 1, 20),   -- normal: 20 metafases contadas
    (402, 202, 1, 25),   -- Down: 25 (se cuenta más ante hallazgo)
    (403, 203, 1, 30);   -- Klinefelter: 30 (descarta mosaicismo 46,XY/47,XXY)
SET IDENTITY_INSERT SCAContador OFF;

/* --- Cromosomas destacados por metafase (los anómalos / de interés) --------- */
/* SCACromosomas guarda un recorte por cromosoma + comentario; acá sólo los    */
/* relevantes (el complemento completo son 46-47 filas por análisis).          */
SET IDENTITY_INSERT SCACromosomas ON;
INSERT INTO SCACromosomas (IdCromosoma, IdAnalisis, ImagenCromosoma, ComentariosCromosoma) VALUES
    -- M1 (301): normal, sin anomalías destacadas
    (501, 301, NULL, N'Par 21 normal (dos copias).'),
    -- M2 (302): trisomía 21
    (502, 302, NULL, N'Par 21: TRES copias — trisomía libre (+21).'),
    (503, 302, NULL, N'Resto del complemento sin anomalías estructurales.'),
    -- M3 (303): XXY
    (504, 303, NULL, N'Cromosoma X: dos copias.'),
    (505, 303, NULL, N'Cromosoma Y: una copia — complemento XXY.');
SET IDENTITY_INSERT SCACromosomas OFF;

/* ===========================================================================
   Resumen de las 3 metafases reconstruidas:
     M1  CHN-2026-07-24-0101  46,XX      normal femenino      (20 metafases)
     M2  CHN-2026-07-24-0102  47,XY,+21  Down (trisomía 21)   (25 metafases)
     M3  CHN-2026-07-24-0103  47,XXY     Klinefelter          (30 metafases)
   =========================================================================== */
