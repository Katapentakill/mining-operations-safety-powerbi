// Montaje del video del informe en el Power BI Service (toma 5): recorta al lienzo, sonidos de clic/teclas, música y subtítulos ES/EN.
//   node componer_web.mjs   (desde la carpeta kit)  ->  ../video_web_es.mp4 y ../video_web_en.mp4
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { FFMPEG, sintetizarEfectos, escribirWav, lechoDeMusica, mezclar, duracionDe } from './src/sonido.mjs';
import { SONIDO } from './src/config.mjs';

SONIDO.musica = Number(process.env.MUSICA || 0.13);
const W = path.resolve('..');
const TOMA = 'toma5';
const EPOCA0 = 1795313542125; // época (ms) del segundo 0 del archivo de video (medida con el fundido negro del inicio)
const vt = (t) => (t - EPOCA0) / 1000;

const ev = fs.readFileSync(path.join(W, `${TOMA}_events.txt`), 'utf8').trim().split(/\r?\n/).map((l) => {
  const [t, k, x, y, label] = l.split('|');
  return { t: Number(t), k, x: Number(x), y: Number(y), label };
});
const marca = (k, label) => ev.find((e) => e.k === k && (!label || e.label === label));
const coverOff = marca('cover_off'), coverEnd = marca('cover_end');
const S = vt(coverOff.t) - 0.05;
const E = vt(coverEnd.t) + 1.45;
const DURACION = E - S;
const rel = (t) => vt(t) - S;
const clic = (label, nth = 0) => ev.filter((e) => e.k === 'click' && e.label === label)[nth];
const VIS = 0.6; // el cambio de página se ve ~0,6 s después del clic

// ---------- subtítulos (tiempos del video final) ----------
const T = (lab, n = 0) => rel(clic(lab, n).t);
const ESC = [
  { de: 0.9, a: T('nav Resumen') + VIS - 0.1, es: 'Datos reales de seguridad minera: MSHA, el regulador de EE. UU., y las 43 minas de Freeport-McMoRan (2000–2026).', en: "Real mine-safety data: MSHA, the US regulator, for Freeport-McMoRan's 43 mines (2000–2026)." },
  { de: T('nav Resumen') + VIS, a: T('año abrir', 0) - 0.2, es: '6.654 accidentes y 19.046 infracciones en 26 años. El título de cada página ya dice la conclusión.', en: '6,654 accidents and 19,046 violations over 26 years. Each page title states the conclusion.' },
  { de: T('año abrir', 0), a: T('año abrir', 1) - 0.1, es: 'Al elegir un año, el título y las tarjetas se recalculan y se comparan con el año anterior.', en: 'Pick a year and the title and cards recalculate against the previous year.' },
  { de: T('año abrir', 1), a: T('nav Accidentes') + VIS - 0.1, es: 'Sin año elegido, el informe vuelve a mostrar todo el período.', en: 'With no year selected, the report shows the whole period again.' },
  { de: T('nav Accidentes') + VIS, a: T('nav Infracciones') + VIS - 0.1, es: 'Accidentes: 15 fatalidades desde 2000, con gravedad, tipos, partes del cuerpo y áreas de trabajo.', en: 'Accidents: 15 fatalities since 2000, by severity, type, body part and work area.' },
  { de: T('nav Infracciones') + VIS, a: T('nav Plantilla') + VIS - 0.1, es: 'Infracciones: las normas más citadas y US$ 12,2 millones en multas pagadas.', en: 'Violations: the most-cited standards and US$12.2 million in fines paid.' },
  { de: T('nav Plantilla') + VIS, a: T('nav Mapa') + VIS - 0.1, es: 'Plantilla: horas trabajadas y tasa de incidencia. La seguridad se mide contra la exposición.', en: 'Workforce: hours worked and incidence rate. Safety is measured against exposure.' },
  { de: T('nav Mapa') + VIS, a: T('ranking Morenci') + 0.4, es: 'Morenci concentra el 44 % de los accidentes.', en: 'Morenci accounts for 44 % of accidents.' },
  { de: T('ranking Morenci') + 0.5, a: T('nav Detalle') + VIS - 0.1, es: 'Un clic en el mapa, el ranking o la tabla abre la ficha de la mina.', en: 'One click on the map, ranking or table opens the mine card.' },
  { de: T('nav Detalle') + VIS, a: T('nav Resumen', 1) + VIS - 0.1, es: 'En Detalle se busca una mina escribiendo su nombre y todo el informe se filtra a ella.', en: 'On Detail you search a mine by typing its name and the whole page filters to it.' },
  { de: T('nav Resumen', 1) + VIS, a: rel(coverEnd.t) + 0.5, es: 'Modelo en estrella sobre SQL Server, informe como código (PBIP/TMDL), con pruebas y CI.', en: 'Star schema on SQL Server, report as code (PBIP/TMDL), with tests and CI.' },
];
const t2s = (s) => {
  const ms = Math.round(Math.max(0, s) * 1000);
  const p = (n, l = 2) => String(n).padStart(l, '0');
  return `${p(Math.floor(ms / 3600000))}:${p(Math.floor((ms % 3600000) / 60000))}:${p(Math.floor((ms % 60000) / 1000))},${p(ms % 1000, 3)}`;
};
for (const lang of ['es', 'en']) {
  fs.writeFileSync(path.join(W, `subs_web_${lang}.srt`), ESC.map((e, i) => `${i + 1}\n${t2s(e.de)} --> ${t2s(Math.min(DURACION, e.a))}\n${e[lang]}\n`).join('\n'), 'utf8');
}
console.log(`inicio ${S.toFixed(2)} s, fin ${E.toFixed(2)} s, duración ${DURACION.toFixed(1)} s`);

// ---------- audio ----------
const efectosEv = [
  ...ev.filter((e) => e.k === 'click').map((e) => ({ tipo: 'clic', t: rel(e.t) * 1000 - 60 })),
  ...ev.filter((e) => e.k === 'key').map((e) => ({ tipo: 'tecla', clase: 'letra', t: rel(e.t) * 1000 - 60 })),
];
console.log(`clics: ${efectosEv.filter((e) => e.tipo === 'clic').length}, teclas: ${efectosEv.filter((e) => e.tipo === 'tecla').length}`);
escribirWav(path.join(W, 'efectos_web.wav'), sintetizarEfectos(efectosEv, 0, DURACION));
lechoDeMusica(DURACION, path.join(W, 'musica_web.wav'));

// ---------- video: lienzo del informe (1470x827 en 124,141) -> 1664x936 centrado en 1920x1080, banda inferior para subtítulos ----------
const estilo = "FontName=Segoe UI Semibold,FontSize=10,PrimaryColour=&H00FFFFFF&,OutlineColour=&H80000000&,BorderStyle=1,Outline=2,Shadow=0,MarginV=12,MarginL=18,MarginR=18,Alignment=2";
for (const lang of ['es', 'en']) {
  const sinAudio = path.join(W, `silencioso_web_${lang}.mp4`);
  const graph = `[0:v]trim=${S.toFixed(3)}:${E.toFixed(3)},setpts=PTS-STARTPTS,fps=30,crop=1470:827:124:141,scale=1664:936:flags=lanczos,pad=1920:1080:128:0:color=0x11151c,subtitles=subs_web_${lang}.srt:force_style='${estilo}'[out]`;
  const r = spawnSync(FFMPEG, ['-hide_banner', '-y', '-i', `${TOMA}.mkv`, '-filter_complex', graph, '-map', '[out]', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', sinAudio], { cwd: W, encoding: 'utf8', maxBuffer: 1 << 28 });
  if (r.status !== 0) { console.error(r.stderr.slice(-2500)); process.exit(1); }
  mezclar({ video: sinAudio, efectos: path.join(W, 'efectos_web.wav'), musica: path.join(W, 'musica_web.wav'), salida: path.join(W, `video_web_${lang}.mp4`) });
  console.log(`✓ video_web_${lang}.mp4 · ${duracionDe(path.join(W, `video_web_${lang}.mp4`)).toFixed(1)} s`);
}
