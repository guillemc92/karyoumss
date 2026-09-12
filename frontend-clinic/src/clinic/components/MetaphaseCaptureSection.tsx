import { useRef, useState } from 'react';
import { useCamera } from '../hooks/useCamera';
import type { CapturedImage } from '../types/registration';

interface MetaphaseCaptureSectionProps {
  images: CapturedImage[];
  onChange: (images: CapturedImage[]) => void;
}

const MIN_RECOMMENDED = 20;

export function MetaphaseCaptureSection({ images, onChange }: MetaphaseCaptureSectionProps) {
  const camera = useCamera();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [brightness, setBrightness] = useState(0);
  const [contrast, setContrast] = useState(0);
  const [threshold, setThreshold] = useState(50);
  const [resolution, setResolution] = useState('1024x768');

  function handleCapture() {
    const data = camera.capture(brightness, contrast);
    if (data) {
      onChange([...images, { data_base64: data, source: 'camera' }]);
    }
  }

  function readFileAsDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const result = event.target?.result;
        if (typeof result === 'string') resolve(result);
        else reject(new Error('FileReader result was not a string'));
      };
      reader.onerror = () => reject(reader.error ?? new Error('FileReader failed'));
      reader.readAsDataURL(file);
    });
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (fileInputRef.current) fileInputRef.current.value = '';
    const dataUrls = await Promise.all(files.map(readFileAsDataUrl));
    const newImages: CapturedImage[] = dataUrls.map((data_base64) => ({ data_base64, source: 'upload' }));
    onChange([...images, ...newImages]);
  }

  function handleDelete(index: number) {
    onChange(images.filter((_, i) => i !== index));
  }

  function handleClearAll() {
    if (window.confirm('¿Eliminar todas las metafases capturadas?')) {
      onChange([]);
    }
  }

  const isQualityGood = images.length >= MIN_RECOMMENDED;

  return (
    <div className="form-section">
      <div className="form-section-title"><i className="fas fa-camera"></i> Captura de Metafases</div>

      <div className="capture-container">
        <div className="camera-panel">
          <div className="camera-header">
            <span><i className="fas fa-video"></i> Vista previa</span>
            <span>{camera.isConnected ? '✅ Cámara conectada' : '📷 Cámara desconectada'}</span>
          </div>
          <div className="camera-preview">
            {camera.isConnected ? (
              <video ref={camera.videoRef} autoPlay style={{ width: '100%', maxHeight: '280px', borderRadius: '8px' }} />
            ) : (
              <div className="preview-placeholder">
                <i className="fas fa-camera"></i>
                <p>Conecte una cámara o seleccione un archivo</p>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ marginTop: '10px', padding: '8px 16px', fontSize: '0.7rem' }}
                  onClick={camera.connect}
                >
                  <i className="fas fa-plug"></i> Conectar cámara
                </button>
              </div>
            )}
          </div>
          <div className="camera-controls">
            {camera.isConnected && (
              <button type="button" className="btn btn-outline" onClick={camera.disconnect}>
                Desconectar cámara
              </button>
            )}
            <button type="button" className="btn btn-primary" disabled={!camera.isConnected} onClick={handleCapture}>
              <i className="fas fa-camera"></i> Capturar metafase
            </button>
            <button type="button" className="btn btn-outline" onClick={() => fileInputRef.current?.click()}>
              <i className="fas fa-upload"></i> Subir imagen
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/tiff"
              multiple
              style={{ display: 'none' }}
              onChange={handleFileUpload}
            />
          </div>
          {camera.error && <p style={{ color: 'var(--umss-red)', fontSize: '0.7rem', padding: '0 15px 10px' }}>{camera.error}</p>}
        </div>

        <div className="adjust-panel">
          <div className="adjust-header"><i className="fas fa-sliders-h"></i> Ajustes de imagen</div>
          <div className="adjust-body">
            <div className="slider-group">
              <label>Brillo <span>{brightness}</span></label>
              <input type="range" min={-100} max={100} value={brightness} onChange={(e) => setBrightness(Number(e.target.value))} />
            </div>
            <div className="slider-group">
              <label>Contraste <span>{contrast}</span></label>
              <input type="range" min={-100} max={100} value={contrast} onChange={(e) => setContrast(Number(e.target.value))} />
            </div>
            <div className="slider-group">
              <label>Umbral (Threshold) <span>{threshold}</span></label>
              <input type="range" min={0} max={100} value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} />
            </div>
            <div className="slider-group">
              <label>Resolución</label>
              <select className="form-input" value={resolution} onChange={(e) => setResolution(e.target.value)}>
                <option value="640x480">640x480</option>
                <option value="800x600">800x600</option>
                <option value="1024x768">1024x768</option>
                <option value="1280x960">1280x960</option>
              </select>
            </div>
            <div style={{ marginTop: '12px' }}>
              <span className={`quality-badge ${isQualityGood ? 'quality-good' : 'quality-warning'}`}>
                <i className={`fas ${isQualityGood ? 'fa-check-circle' : 'fa-exclamation-triangle'}`}></i>
                {isQualityGood
                  ? ` Calidad: Suficiente (${images.length}/${MIN_RECOMMENDED})`
                  : ` Faltan ${MIN_RECOMMENDED - images.length} metafases (mínimo ${MIN_RECOMMENDED})`}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="gallery-section">
        <div className="gallery-title">
          <span><i className="fas fa-images"></i> Metafases capturadas ({images.length}/{MIN_RECOMMENDED} mínimas)</span>
          <button type="button" className="btn btn-outline" style={{ padding: '4px 12px', fontSize: '0.7rem' }} onClick={handleClearAll}>
            <i className="fas fa-trash"></i> Limpiar todas
          </button>
        </div>
        <div className="gallery-grid">
          {images.length === 0 ? (
            <div style={{ gridColumn: '1/-1', textAlign: 'center', color: 'var(--gray-text)', padding: '20px' }}>
              No hay metafases capturadas. Conecte una cámara o suba imágenes.
            </div>
          ) : (
            images.map((img, idx) => (
              <div className="gallery-item" key={idx}>
                <div className="gallery-thumb">
                  <img src={img.data_base64} alt={`Metafase ${idx + 1}`} />
                </div>
                <div className="gallery-label">Metafase {idx + 1}</div>
                <div className="delete-image" onClick={() => handleDelete(idx)}>
                  <i className="fas fa-times"></i>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
