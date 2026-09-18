import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { DictProvider } from './provider/DictProvider'
import 'antd/dist/reset.css'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <DictProvider>
      <App />
    </DictProvider>
  </React.StrictMode>
)