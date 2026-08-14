import { createHashRouter, RouterProvider, Navigate } from "react-router-dom";
import { Layout } from "../layouts/Layout";
import { PublicLayout } from "../layouts/PublicLayout";
import { AuthLayout } from "../layouts/AuthLayout";

import { LandingView } from "../views/LandingView";
import { PricingView } from "../views/PricingView";
import { LoginView } from "../views/LoginView";
import { RegisterView } from "../views/RegisterView";
import { ForgotPasswordView } from "../views/ForgotPasswordView";
import { TelegramCallbackView } from "../views/TelegramCallbackView";

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
import { AddDeviceWizard } from "../views/AddDeviceWizard";
import { AddCameraWizard } from "../views/AddCameraWizard";
import { FamilySharingView } from "../views/FamilySharingView";
import { SubscriptionView } from "../views/SubscriptionView";
import { CheckoutView } from "../views/CheckoutView";
import { InvoiceListView } from "../views/InvoiceListView";
import {
  DeviceDetailView,
  AccountSettingsView
} from "../views/Placeholders";

const router = createHashRouter([
  {
    element: <PublicLayout />,
    children: [
      { path: "/", element: <LandingView /> },
      { path: "/pricing", element: <PricingView /> },
    ]
  },
  {
    element: <AuthLayout />,
    children: [
      { path: "/login", element: <LoginView /> },
      { path: "/register", element: <RegisterView /> },
      { path: "/forgot-password", element: <ForgotPasswordView /> },
      { path: "/telegram-callback", element: <TelegramCallbackView /> },
    ]
  },
  {
    element: <Layout />,
    children: [
      { path: "/dashboard", element: <DashboardView /> },
      { path: "/cameras", element: <CameraListView /> },
      { path: "/cameras/add", element: <AddCameraWizard /> },
      { path: "/cameras/:id", element: <CameraDetailView /> },
      { path: "/roi", element: <ROIListView /> },
      { path: "/roi/:cameraId", element: <ROIDrawingView /> },
      { path: "/alerts", element: <AlertListView /> },
      { path: "/alerts/:id", element: <AlertDetailView /> },
      { path: "/devices", element: <DeviceListView /> },
      { path: "/devices/add", element: <AddDeviceWizard /> },
      { path: "/devices/:id", element: <DeviceDetailView /> },
      { path: "/children", element: <ChildrenProfilesView /> },
      { path: "/settings/notifications", element: <NotificationsSettingsView /> },
      { path: "/settings/privacy", element: <PrivacySettingsView /> },
      { path: "/settings/family", element: <FamilySharingView /> },
      { path: "/billing", element: <SubscriptionView /> },
      { path: "/billing/checkout", element: <CheckoutView /> },
      { path: "/billing/invoices", element: <InvoiceListView /> },
      { path: "/account", element: <AccountSettingsView /> },
    ]
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  }
]);

export const AppRouter = () => {
  return <RouterProvider router={router} />;
};
