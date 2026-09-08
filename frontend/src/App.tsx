import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { getToken } from './api'
import MainLayout from './layouts/MainLayout'
import LoginPage from './pages/Login'
import Dashboard from './pages/Dashboard'
import Groups from './pages/Groups'
import Positions from './pages/Positions'
import Rules from './pages/Rules'
import Tasks from './pages/Tasks'

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
        <Route path="groups" element={<Groups />} />
        <Route path="positions" element={<Positions />} />
        <Route path="rules" element={<Rules />} />
        <Route path="tasks" element={<Tasks />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  </BrowserRouter>
)

export default App