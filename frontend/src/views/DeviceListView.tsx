import React from "react";
import { useSystemStatusStore } from "../store/systemStatusStore";
import { useCameraStore } from "../store/cameraStore";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/Toast";

export const DeviceListView: React.FC = () => {
  const { showToast } = useToast();
  const { deviceInfo, complianceChecks } = useSystemStatusStore();
  const { cameras } = useCameraStore();

  const handleTestConnection = (name: string) => {
    showToast(`Đang kiểm tra tín hiệu Ping tới ${name}...`, "info");
    setTimeout(() => {
      showToast(`Kết nối tới ${name} ổn định (Ping: 14ms)`, "success");
    }, 1500);
  };

  const handleConfigure = (name: string) => {
    showToast(`Mở hộp thoại cấu hình thiết bị ${name} (Tính năng đang phát triển)`, "info");
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div>
        <h2 className="text-xl md:text-2xl font-bold text-on-surface">Quản lý thiết bị phần cứng</h2>
        <p className="text-sm text-on-surface-variant mt-1">
          Theo dõi cấu hình, hiệu năng phần cứng và độ tuân thủ tiêu chuẩn an ninh thông tin.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: List of Devices */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="font-bold text-on-surface text-base">Thiết bị trong mạng nội bộ</h3>

          <div className="flex flex-col gap-4">
            
            {/* Gateway Hub Device Card */}
            {deviceInfo && (
              <div className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-bold text-base text-on-surface flex items-center gap-2">
                      {deviceInfo.name}
                      <StatusBadge type={deviceInfo.status} />
                    </h4>
                    <p className="text-xs text-on-surface-variant mt-0.5">Mã thiết bị: {deviceInfo.id}</p>
                  </div>
                  <span className="px-2.5 py-1 bg-primary/10 text-primary rounded-lg text-xs font-bold uppercase shrink-0">
                    Gateway Hub
                  </span>
                </div>

                {/* Diagnostics */}
                <div className="grid grid-cols-3 gap-4 py-2 border-t border-b border-outline-variant/10 text-center">
                  <div>
                    <p className="text-[10px] font-semibold text-on-surface-variant">Tải CPU</p>
                    <p className="text-sm font-bold text-on-surface mt-0.5">{deviceInfo.cpuUsage}%</p>
                    <div className="w-full bg-surface-container-low h-1.5 rounded-full overflow-hidden mt-1.5 max-w-[80px] mx-auto">
                      <div className="bg-primary h-full" style={{ width: `${deviceInfo.cpuUsage}%` }}></div>
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold text-on-surface-variant">Tải RAM</p>
                    <p className="text-sm font-bold text-on-surface mt-0.5">{deviceInfo.memoryUsage} MB</p>
                    <div className="w-full bg-surface-container-low h-1.5 rounded-full overflow-hidden mt-1.5 max-w-[80px] mx-auto">
                      <div className="bg-secondary h-full" style={{ width: '40%' }}></div>
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold text-on-surface-variant">Bộ nhớ trống</p>
                    <p className="text-sm font-bold text-on-surface mt-0.5">{deviceInfo.diskFreeGb} GB</p>
                    <p className="text-[8px] text-on-surface-variant mt-1">Hạn mức: 32 GB</p>
                  </div>
                </div>

                <div className="flex flex-wrap justify-between items-center gap-3 text-xs">
                  <div className="space-y-0.5 text-on-surface-variant font-medium">
                    <p>Địa chỉ IP: <span className="font-semibold text-on-surface">{deviceInfo.ipAddress}</span></p>
                    <p>Địa chỉ MAC: <span className="font-semibold text-on-surface">{deviceInfo.macAddress}</span></p>
                    <p>Phiên bản: <span className="font-semibold text-on-surface">{deviceInfo.firmwareVersion}</span></p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleTestConnection(deviceInfo.name)}
                      className="py-1.5 px-3.5 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg font-bold transition-all focus:outline-none"
                    >
                      Kiểm tra kết nối
                    </button>
                    <button
                      onClick={() => handleConfigure(deviceInfo.name)}
                      className="py-1.5 px-3.5 bg-primary hover:bg-primary/95 text-white rounded-lg font-bold transition-all focus:outline-none"
                    >
                      Cấu hình
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Camera devices listed */}
            {cameras.map((cam) => (
              <div key={cam.id} className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-bold text-base text-on-surface flex items-center gap-2">
                      Camera {cam.name}
                      <StatusBadge type={cam.status} />
                    </h4>
                    <p className="text-xs text-on-surface-variant mt-0.5">Vị trí đặt: {cam.location}</p>
                  </div>
                  <span className="px-2.5 py-1 bg-secondary/10 text-secondary rounded-lg text-xs font-bold uppercase shrink-0">
                    Edge IP Camera
                  </span>
                </div>

                <div className="flex flex-wrap justify-between items-center gap-3 text-xs pt-2 border-t border-outline-variant/10">
                  <div className="space-y-0.5 text-on-surface-variant font-medium">
                    <p>Địa chỉ IP: <span className="font-semibold text-on-surface">192.168.1.{cam.id === 'camera_living_room_01' ? '41' : cam.id === 'camera_balcony_01' ? '42' : '43'}</span></p>
                    <p>Tốc độ quét: <span className="font-semibold text-on-surface">{cam.fps} FPS ({cam.resolution})</span></p>
                    <p>Độ mạnh Wi-Fi: <span className="font-semibold text-on-surface capitalize">{cam.signalQuality}</span></p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleTestConnection(`Camera ${cam.name}`)}
                      className="py-1.5 px-3.5 bg-surface-container-high hover:bg-surface-container-highest text-on-surface rounded-lg font-bold transition-all focus:outline-none"
                    >
                      Kiểm tra kết nối
                    </button>
                    <button
                      onClick={() => handleConfigure(`Camera ${cam.name}`)}
                      className="py-1.5 px-3.5 bg-primary hover:bg-primary/95 text-white rounded-lg font-bold transition-all focus:outline-none"
                    >
                      Cấu hình
                    </button>
                  </div>
                </div>
              </div>
            ))}

          </div>
        </div>

        {/* Right Column: Security Compliance Checks */}
        <div className="space-y-6">
          <h3 className="font-bold text-on-surface text-base">Độ tuân thủ an ninh (IoT Compliance)</h3>
          
          <div className="flex flex-col gap-4">
            {complianceChecks.map((standard) => (
              <div key={standard.standard} className="bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/30 shadow-sm space-y-4">
                <div className="flex justify-between items-center">
                  <h4 className="font-bold text-sm text-on-surface max-w-[200px] leading-tight">{standard.standard}</h4>
                  <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 rounded text-[10px] font-bold uppercase shrink-0">
                    Đã thông qua
                  </span>
                </div>

                <ul className="space-y-2 text-xs">
                  {standard.checks.map((check) => (
                    <li key={check.id} className="flex items-start gap-2 text-on-surface-variant font-medium">
                      <span className="material-symbols-outlined text-emerald-500 text-[16px] shrink-0 fill mt-0.5">
                        check_circle
                      </span>
                      <div>
                        <span className="font-semibold text-on-surface block">{check.name}</span>
                        <span className="text-[10px] text-outline block">{check.id} • Passed</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};
export default DeviceListView;
