import { AnimatePresence, motion } from 'motion/react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { Footer, Nav } from './components/Chrome'
import { AuthProvider, RequireAuth } from './lib/auth'
import { ThemeContext, useTheme } from './lib/hooks'
import Account from './pages/Account'
import { Forgot, Login, Signup, Verify } from './pages/Auth'
import CheckIn from './pages/CheckIn'
import Join from './pages/Join'
import Landing from './pages/Landing'
import { NotFound, Privacy, Terms } from './pages/Legal'
import Me from './pages/Me'
import OrgPulse from './pages/OrgPulse'
import OrgSettings from './pages/OrgSettings'
import Pricing from './pages/Pricing'
import Start from './pages/Start'

export default function App() {
  const location = useLocation()
  const theme = useTheme()
  const immersive = location.pathname.startsWith('/check-in')

  return (
    <ThemeContext.Provider value={theme.resolved}>
      <AuthProvider>
        <div className="flex min-h-screen flex-col">
          {!immersive && <Nav theme={theme} />}
          <AnimatePresence mode="wait">
            <motion.main
              key={location.pathname.split('/').slice(0, 2).join('/')}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="flex-1"
            >
              <Routes location={location}>
                <Route path="/" element={<Landing />} />
                <Route path="/pricing" element={<Pricing />} />
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
                <Route path="/verify" element={<Verify />} />
                <Route path="/forgot" element={<Forgot />} />
                <Route path="/privacy" element={<Privacy />} />
                <Route path="/terms" element={<Terms />} />
                <Route path="/join/:code" element={<Join />} />
                <Route path="/start" element={<RequireAuth><Start /></RequireAuth>} />
                <Route path="/account" element={<RequireAuth><Account /></RequireAuth>} />
                <Route path="/check-in" element={<RequireAuth><CheckIn /></RequireAuth>} />
                <Route path="/me" element={<RequireAuth><Me /></RequireAuth>} />
                <Route path="/org" element={<RequireAuth><OrgPulse /></RequireAuth>} />
                <Route path="/org/:orgId" element={<RequireAuth><OrgPulse /></RequireAuth>} />
                <Route path="/org/:orgId/settings" element={<RequireAuth><OrgSettings /></RequireAuth>} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </motion.main>
          </AnimatePresence>
          {!immersive && <Footer />}
        </div>
      </AuthProvider>
    </ThemeContext.Provider>
  )
}
