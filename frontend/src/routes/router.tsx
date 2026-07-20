import { createHashRouter, RouterProvider, Navigate } from "react-router-dom";
import { Layout } from "../layouts/Layout";
import { LoginView } from "../views/LoginView";
import { DashboardView } from "../views/DashboardView";
import { PrivacySettingsView } from "../views/PrivacySettingsView";
import { AlertListView } from "../views/AlertListView";
import { ROIDrawingView } from "../views/ROIDrawingView";
import { CameraListView } from "../views/CameraListView";
import { CameraDetailView } from "../views/CameraDetailView";
import { AlertDetailView } from "../views/AlertDetailView";
import { DeviceListView } from "../views/DeviceListView";
import { ChildrenProfilesView } from "../views/ChildrenProfilesView";
import { NotificationsSettingsView } from "../views/NotificationsSettingsView";
import { ROIListView } from "../views/ROIListView";
import {
  DeviceDetailView,
  AccountSettingsView
} from "../views/Placeholders";

const router = createHashRouter([
  {
    path: "/login",
    element: <LoginView />,
  },
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        path: "",
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: "dashboard",
        element: <DashboardView />,
      },
      {
        path: "cameras",
        element: <CameraListView />,
      },
      {
        path: "cameras/:id",
        element: <CameraDetailView />,
      },
      {
        path: "roi",
        element: <ROIListView />,
      },
      {
        path: "roi/:cameraId",
        element: <ROIDrawingView />,
      },
      {
        path: "alerts",
        element: <AlertListView />,
      },
      {
        path: "alerts/:id",
        element: <AlertDetailView />,
      },
      {
        path: "devices",
        element: <DeviceListView />,
      },
      {
        path: "devices/:id",
        element: <DeviceDetailView />,
      },
      {
        path: "children",
        element: <ChildrenProfilesView />,
      },
      {
        path: "settings/notifications",
        element: <NotificationsSettingsView />,
      },
      {
        path: "settings/privacy",
        element: <PrivacySettingsView />,
      },
      {
        path: "account",
        element: <AccountSettingsView />,
      }
    ]
  },
  {
    path: "*",
    element: <Navigate to="/dashboard" replace />,
  }
]);

export const AppRouter = () => {
  return <RouterProvider router={router} />;
};
