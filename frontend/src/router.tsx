import { Navigate, createBrowserRouter } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { ExperimentResults } from "./components/ExperimentResults";
import { FlagEditor } from "./components/FlagEditor";
import { AppLayout } from "./layouts/AppLayout";
import { FlagLayout } from "./layouts/FlagLayout";
import { ProjectLayout } from "./layouts/ProjectLayout";
import { Root } from "./layouts/Root";
import { FlagSdkPage } from "./pages/flag/FlagSdkPage";
import { FlagTestPage } from "./pages/flag/FlagTestPage";
import { FlagsListPage } from "./pages/FlagsListPage";
import { KeysPage } from "./pages/KeysPage";
import { LoginPage } from "./pages/LoginPage";
import { MembersPage } from "./pages/MembersPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SettingsPage } from "./pages/SettingsPage";

export const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      { path: "/login", element: <LoginPage /> },
      {
        path: "/",
        element: (
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        ),
        children: [
          { index: true, element: <Navigate to="/projects" replace /> },
          { path: "projects", element: <ProjectsPage /> },
          { path: "profile", element: <ProfilePage /> },
          {
            path: "projects/:projectId",
            element: <ProjectLayout />,
            children: [
              { index: true, element: <Navigate to="flags" replace /> },
              { path: "flags", element: <FlagsListPage /> },
              {
                path: "flags/:flagKey",
                element: <FlagLayout />,
                children: [
                  { index: true, element: <FlagEditor /> },
                  { path: "test", element: <FlagTestPage /> },
                  { path: "results", element: <ExperimentResults /> },
                  { path: "sdk", element: <FlagSdkPage /> },
                ],
              },
              { path: "keys", element: <KeysPage /> },
              { path: "members", element: <MembersPage /> },
              { path: "settings", element: <SettingsPage /> },
            ],
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
]);
