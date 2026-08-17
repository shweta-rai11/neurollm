import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import QuestionLab from './pages/QuestionLab'
import ActivationExplorer from './pages/ActivationExplorer'
import ExperimentLab from './pages/ExperimentLab'
import UncertaintyLab from './pages/UncertaintyLab'
import FingerprintDetection from './pages/FingerprintDetection'
import History from './pages/History'
import About from './pages/About'
import ProfileLayout from './pages/profile/ProfileLayout'
import Enroll from './pages/profile/Enroll'
import Overview from './pages/profile/Overview'
import Evolution from './pages/profile/Evolution'
import Counterfactual from './pages/profile/Counterfactual'
import Research from './pages/profile/Research'
import Privacy from './pages/profile/Privacy'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/question-lab" element={<QuestionLab />} />
          <Route path="/activation-explorer" element={<ActivationExplorer />} />
          <Route path="/experiment-lab" element={<ExperimentLab />} />
          <Route path="/uncertainty-lab" element={<UncertaintyLab />} />
          <Route path="/fingerprint-detection" element={<FingerprintDetection />} />
          <Route path="/history" element={<History />} />
          <Route path="/about" element={<About />} />
          <Route path="/profile" element={<ProfileLayout />}>
            <Route index element={<Overview />} />
            <Route path="enroll" element={<Enroll />} />
            <Route path="evolution" element={<Evolution />} />
            <Route path="counterfactual" element={<Counterfactual />} />
            <Route path="research" element={<Research />} />
            <Route path="privacy" element={<Privacy />} />
          </Route>
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
