// authContextInstance.js
// Just the createContext() call, isolated in its own file. AuthContext.jsx
// (a component) and useAuth.js (a hook) both need this same instance, but
// neither file can export it directly without breaking Vite's Fast Refresh
// (a file must export only components, or only non-component values — never
// both, per eslint's react-refresh/only-export-components rule).

import { createContext } from "react";

export const AuthContext = createContext(null);
