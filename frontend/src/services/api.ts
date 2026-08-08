const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8007/api';

export const fetchCamerasApi = async () => {
  try {
    const res = await fetch(`${API_BASE}/cameras`);
    if (!res.ok) throw new Error('Không thể kết nối đến server');
    return await res.json();
  } catch (err) {
    console.warn('API Error (sử dụng fallback local):', err);
    return null;
  }
};

export const fetchAlertsApi = async () => {
  try {
    const res = await fetch(`${API_BASE}/alerts`);
    if (!res.ok) throw new Error('Không thể kết nối đến server');
    return await res.json();
  } catch (err) {
    console.warn('API Error (sử dụng fallback local):', err);
    return null;
  }
};

export const saveCameraRoiApi = async (cameraId: string, zones: any[]) => {
  try {
    const res = await fetch(`${API_BASE}/cameras/${cameraId}/roi`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(zones)
    });
    if (!res.ok) throw new Error('Lỗi lưu cấu hình ROI');
    return await res.json();
  } catch (err) {
    console.error('Lỗi khi lưu ROI:', err);
    return null;
  }
};

export const updateAlertStatusApi = async (alertId: string | number, status: string, notes?: string) => {
  try {
    const res = await fetch(`${API_BASE}/alerts/${alertId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, notes })
    });
    if (!res.ok) throw new Error('Lỗi cập nhật cảnh báo');
    return await res.json();
  } catch (err) {
    console.error('Lỗi khi cập nhật cảnh báo:', err);
    return null;
  }
};
