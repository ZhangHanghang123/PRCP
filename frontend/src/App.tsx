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
import ModelManage from './pages/ModelManage'
import ReverseCalc from './pages/ReverseCalc'
import RateCurve from './pages/RateCurve'
import SimSchemeList from './pages/SimSchemeList'
import SimConfigPage from './pages/SimConfigPage'
import SimResultPage from './pages/SimResultPage'
import EsgSchemes from './pages/EsgSchemes'
import EsgSchemeDetail from './pages/EsgSchemeDetail'
import EsgCurve from './pages/EsgCurve'
import EsgResults from './pages/EsgResults'
import MetricCoefficient from './pages/MetricCoefficient'
import ReverseMetricTable from './pages/ReverseMetricTable'

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
        <Route path="kpi" element={<KPI />} />
        <Route path="data-maint" element={<DataMaint />}>
          <Route path=":category" element={<DataMaint />} />
        </Route>
        <Route path="system" element={<System />} />
        <Route path="model" element={<ModelManage />} />
        <Route path="reverse" element={<ReverseCalc />} />
        <Route path="rate" element={<RateCurve />} />
        <Route path="sim/list" element={<SimSchemeList />} />
        <Route path="sim/config/:scheme_id" element={<SimConfigPage />} />
        <Route path="sim/results/:sim_scheme_code" element={<SimResultPage />} />
        <Route path="esg" element={<EsgSchemes />} />
        <Route path="esg/detail/:scheme_id" element={<EsgSchemeDetail />} />
        <Route path="esg/curve" element={<EsgCurve />} />
        <Route path="esg/results" element={<EsgResults />} />
        <Route path="metric-coefficient" element={<MetricCoefficient />} />
        <Route path="reverse-metric-table" element={<ReverseMetricTable />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  </BrowserRouter>
)

export default App