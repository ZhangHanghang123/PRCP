import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { getToken } from './api'
import MainLayout from './layouts/MainLayout'
import LoginPage from './pages/Login'
import Dashboard from './pages/Dashboard'
import COA from './pages/COA'
import Reports from './pages/Reports'
import BalanceSheet from './pages/BalanceSheet'
import KPI from './pages/KPI'
import DataMaint from './pages/DataMaint'
import System from './pages/System'

const PrivateRoute = ({ children }: { children: React.ReactNode }) =>
  getToken() ? <>{children}</> : <Navigate to="/login" replace />

const App: React.FC = () => (
  <BrowserRouter basename="/prcp">
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <MainLayout />
          </PrivateRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="coa" element={<COA />} />
        <Route path="reports" element={<Reports />} />
        <Route path="balance" element={<BalanceSheet />} />
        <Route path="kpi" element={<KPI />} />
        <Route path="data-maint" element={<DataMaint />}>
          <Route path=":category" element={<DataMaint />} />
        </Route>
        <Route path="system" element={<System />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  </BrowserRouter>
)

export default App