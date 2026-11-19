import { useEffect, useRef, useState } from 'react';
import Avatar from './components/Avatar.jsx';
import BotonMicrofono from './components/BotonMicrofono.jsx';
import BotonesError from './components/BotonesError.jsx';
import RespuestaSara from './components/RespuestaSara.jsx';

const MENSAJE_INICIAL =
  'Presiona el micrófono y cuéntame qué necesitas organizar.';
const MENSAJES_ESTADO = {
  escuchando: 'Te escucho. Presiona el botón cuando termines de hablar.',
  pensando: 'Estoy procesando tu mensaje...',
};

function blobComoWav(blob) {
  return new Promise((resolve, reject) => {
    const lector = new FileReader();
    lector.onerror = () => reject(new Error('No se pudo leer la grabación.'));
    lector.onload = async () => {
      let contexto;

      try {
        contexto = new AudioContext();
        const audio = await contexto.decodeAudioData(lector.result);
        const frecuenciaMuestreo = 16000;
        const proporcion = audio.sampleRate / frecuenciaMuestreo;
        const longitud = Math.floor(audio.length / proporcion);
        const muestras = new Float32Array(longitud);

        for (let indice = 0; indice < longitud; indice += 1) {
          const posicion = indice * proporcion;
          const inicio = Math.floor(posicion);
          const fraccion = posicion - inicio;
          let suma = 0;

          for (let canal = 0; canal < audio.numberOfChannels; canal += 1) {
            const datos = audio.getChannelData(canal);
            const muestraInicial = datos[inicio] ?? 0;
            const muestraFinal = datos[Math.min(inicio + 1, audio.length - 1)];
            suma += muestraInicial + (muestraFinal - muestraInicial) * fraccion;
          }

          muestras[indice] = suma / audio.numberOfChannels;
        }

        const bytesAudio = muestras.length * 2;
        const buffer = new ArrayBuffer(44 + bytesAudio);
        const vista = new DataView(buffer);
        const escribirTexto = (desplazamiento, texto) => {
          for (let indice = 0; indice < texto.length; indice += 1) {
            vista.setUint8(desplazamiento + indice, texto.charCodeAt(indice));
          }
        };

        escribirTexto(0, 'RIFF');
        vista.setUint32(4, 36 + bytesAudio, true);
        escribirTexto(8, 'WAVE');
        escribirTexto(12, 'fmt ');
        vista.setUint32(16, 16, true);
        vista.setUint16(20, 1, true);
        vista.setUint16(22, 1, true);
        vista.setUint32(24, frecuenciaMuestreo, true);
        vista.setUint32(28, frecuenciaMuestreo * 2, true);
        vista.setUint16(32, 2, true);
        vista.setUint16(34, 16, true);
        escribirTexto(36, 'data');
        vista.setUint32(40, bytesAudio, true);

        for (let indice = 0; indice < muestras.length; indice += 1) {
          const muestra = Math.max(-1, Math.min(1, muestras[indice]));
          vista.setInt16(
            44 + indice * 2,
            muestra < 0 ? muestra * 0x8000 : muestra * 0x7fff,
            true,
          );
        }

        resolve(new Blob([buffer], { type: 'audio/wav' }));
      } catch {
        reject(
          new Error(
            'El navegador no pudo convertir la grabación. Intenta con otro navegador.',
          ),
        );
      } finally {
        await contexto?.close();
      }
    };
    lector.readAsArrayBuffer(blob);
  });
}

function blobComoBase64(blob) {
  return new Promise((resolve, reject) => {
    const lector = new FileReader();
    lector.onerror = () => reject(new Error('No se pudo preparar el audio.'));
    lector.onload = () => {
      const resultado = lector.result;
      if (typeof resultado !== 'string') {
        reject(new Error('El formato de audio no es válido.'));
        return;
      }
      resolve(resultado.slice(resultado.indexOf(',') + 1));
    };
    lector.readAsDataURL(blob);
  });
}

function base64ComoBlob(base64) {
  const binario = atob(base64);
  const bytes = new Uint8Array(binario.length);

  for (let indice = 0; indice < binario.length; indice += 1) {
    bytes[indice] = binario.charCodeAt(indice);
  }

  const cabecera = binario.slice(0, 12);
  const tipoAudio = cabecera.startsWith('RIFF')
    ? 'audio/wav'
    : cabecera.startsWith('ID3') ||
        (bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0)
      ? 'audio/mpeg'
      : cabecera.startsWith('OggS')
        ? 'audio/ogg'
        : cabecera.slice(4, 8) === 'ftyp'
          ? 'audio/mp4'
          : 'audio/wav';

  return new Blob([bytes], { type: tipoAudio });
}

async function obtenerMensajeError(respuesta) {
  try {
    const datos = await respuesta.json();
    return datos.detail || `La API respondió con estado ${respuesta.status}.`;
  } catch {
    return `La API respondió con estado ${respuesta.status}.`;
  }
}

export default function App() {
  const [estado, setEstado] = useState('reposo');
  const [mensaje, setMensaje] = useState(MENSAJE_INICIAL);
  const [mensajeError, setMensajeError] = useState('');
  const grabadorRef = useRef(null);
  const flujoRef = useRef(null);
  const fragmentosRef = useRef([]);
  const audioRef = useRef(null);
  const canceladoRef = useRef(false);

  useEffect(
    () => () => {
      grabadorRef.current?.stream?.getTracks().forEach((pista) => pista.stop());
      flujoRef.current?.getTracks().forEach((pista) => pista.stop());
      audioRef.current?.pause();
    },
    [],
  );

  const enviarGrabacion = async (blob) => {
    setEstado('pensando');
    setMensajeError('');
    setMensaje(MENSAJES_ESTADO.pensando);

    try {
      const audioWav = await blobComoWav(blob);
      const audioBase64 = await blobComoBase64(audioWav);
      if (audioBase64.length > 10_000_000) {
        throw new Error('La grabación es demasiado larga. Intenta con un mensaje más corto.');
      }

      const respuesta = await fetch('/api/conversar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_base64: audioBase64 }),
      });

      if (!respuesta.ok) {
        throw new Error(await obtenerMensajeError(respuesta));
      }

      const datos = await respuesta.json();
      if (typeof datos.texto_respuesta !== 'string' || !datos.texto_respuesta.trim()) {
        throw new Error('La API no devolvió una respuesta de texto.');
      }

      setMensaje(datos.texto_respuesta);
      if (typeof datos.audio_base64 === 'string' && datos.audio_base64.length > 0) {
        const audioRespuesta = base64ComoBlob(datos.audio_base64);
        const urlAudio = URL.createObjectURL(audioRespuesta);
        const reproductor = new Audio(urlAudio);
        audioRef.current = reproductor;
        setEstado('hablando');
        reproductor.onended = () => {
          URL.revokeObjectURL(urlAudio);
          setEstado('reposo');
        };
        reproductor.onerror = () => {
          URL.revokeObjectURL(urlAudio);
          setEstado('reposo');
        };
        try {
          await reproductor.play();
        } catch {
          URL.revokeObjectURL(urlAudio);
          setEstado('reposo');
        }
      } else {
        setEstado(datos.texto_respuesta.trim().endsWith('?') ? 'preguntando' : 'reposo');
      }
    } catch (error) {
      flujoRef.current?.getTracks().forEach((pista) => pista.stop());
      flujoRef.current = null;
      setEstado('error');
      setMensajeError(error instanceof Error ? error.message : 'Ocurrió un error inesperado.');
      setMensaje('No pude procesar el audio. Revisa la conexión e inténtalo nuevamente.');
    }
  };

  const iniciarGrabacion = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setEstado('error');
      setMensajeError('Este navegador no permite grabar audio.');
      setMensaje('Usa una versión reciente de Chrome, Edge o Firefox para hablar con S.A.R.A.');
      return;
    }

    try {
      const flujo = await navigator.mediaDevices.getUserMedia({ audio: true });
      flujoRef.current = flujo;
      fragmentosRef.current = [];
      canceladoRef.current = false;
      const grabador = new MediaRecorder(flujo);
      grabadorRef.current = grabador;
      grabador.ondataavailable = (evento) => {
        if (evento.data.size > 0) {
          fragmentosRef.current.push(evento.data);
        }
      };
      grabador.onstop = () => {
        flujo.getTracks().forEach((pista) => pista.stop());
        flujoRef.current = null;
        grabadorRef.current = null;

        if (canceladoRef.current) {
          return;
        }

        const grabacion = new Blob(fragmentosRef.current, {
          type: grabador.mimeType || 'audio/webm',
        });
        void enviarGrabacion(grabacion);
      };
      grabador.start();
      setEstado('escuchando');
      setMensaje(MENSAJES_ESTADO.escuchando);
      setMensajeError('');
    } catch (error) {
      flujoRef.current?.getTracks().forEach((pista) => pista.stop());
      flujoRef.current = null;
      setEstado('error');
      setMensajeError(
        error instanceof Error ? error.message : 'No se pudo acceder al micrófono.',
      );
      setMensaje('No pude activar el micrófono. Revisa los permisos del navegador.');
    }
  };

  const detenerGrabacion = () => {
    if (grabadorRef.current?.state === 'recording') {
      grabadorRef.current.stop();
    }
  };

  const cancelarGrabacion = () => {
    canceladoRef.current = true;
    detenerGrabacion();
    flujoRef.current?.getTracks().forEach((pista) => pista.stop());
    flujoRef.current = null;
    setEstado('cancelado');
    setMensaje('Grabación cancelada. No se envió ningún audio.');
    setMensajeError('');
  };

  const controlarMicrofono = () => {
    if (estado === 'escuchando') {
      detenerGrabacion();
      return;
    }
    void iniciarGrabacion();
  };

  const reintentar = () => {
    setEstado('reposo');
    setMensaje(MENSAJE_INICIAL);
    setMensajeError('');
  };

  return (
    <div className="flex min-h-screen flex-col bg-sara-fondo">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-emerald-100/90 bg-white/80 px-4 py-3.5 backdrop-blur sm:px-8 lg:px-12">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-sara-acento to-[#f8b2cb] text-lg font-black text-white shadow-sm">
            S
          </div>
          <div>
            <h1 className="font-extrabold tracking-tight text-sara-text">
              S.A.R.A.
            </h1>
            <p className="hidden text-xs text-sara-text/60 sm:block">
              Asistente por voz de agenda inteligente
            </p>
          </div>
        </div>
        <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
          Interfaz web
        </span>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col items-center justify-center p-4 sm:p-8 lg:p-12">
        <section
          className="relative flex w-full max-w-[900px] flex-col items-center overflow-hidden rounded-[36px] border border-white/80 bg-sara-superficie p-8 text-center shadow-2xl shadow-emerald-950/10 transition-all duration-300 sm:rounded-[44px] sm:p-10 md:rounded-[48px] md:p-12 lg:p-14"
          aria-label="Panel del asistente S.A.R.A."
        >
          <header className="mx-auto mb-2 w-full max-w-2xl pt-5 sm:pt-0">
            <h2 className="text-3xl font-extrabold leading-tight tracking-tight text-sara-text sm:text-4xl md:text-5xl lg:text-[52px]">
              ¡Hola, soy <span className="text-sara-acento">S.A.R.A.</span>!
            </h2>
            <p className="mt-2 text-xl font-bold tracking-tight text-sara-text/85 sm:text-2xl md:mt-3 md:text-3xl lg:text-[32px]">
              ¿Qué quieres organizar hoy?
            </p>
          </header>

          <div className="my-6 md:my-8 lg:my-9">
            <Avatar estado={estado} />
          </div>

          <div className="mb-6 flex w-full max-w-2xl justify-center md:mb-8">
            <RespuestaSara mensaje={mensaje} estado={estado} />
          </div>

          {estado === 'escuchando' && (
            <button
              type="button"
              onClick={cancelarGrabacion}
              className="mb-4 rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 underline-offset-4 hover:text-rose-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-sara-acento"
            >
              Cancelar grabación
            </button>
          )}

          {estado === 'error' && (
            <div className="mb-5 w-full max-w-2xl" role="alert">
              <p className="text-sm text-rose-700">{mensajeError}</p>
              <BotonesError onReintentar={reintentar} />
            </div>
          )}

          <div className="mb-2 mt-1 md:mt-2">
            <BotonMicrofono
              estado={estado}
              onClick={controlarMicrofono}
              deshabilitado={estado === 'error'}
            />
          </div>

          <footer className="mt-6 flex w-full max-w-md items-center justify-center border-t border-slate-100/80 pt-4 text-xs text-sara-text/50 md:mt-8">
            <span>S.A.R.A. · Asistente de voz</span>
          </footer>
        </section>

        <p className="mt-6 max-w-md text-center text-xs text-sara-text/70 md:text-sm">
          {estado === 'preguntando'
            ? 'Responde en voz alta y vuelve a presionar el micrófono.'
            : 'Presiona el micrófono para hablar. El navegador solicitará permiso la primera vez.'}
        </p>
      </main>
    </div>
  );
}
