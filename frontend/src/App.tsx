import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import Layout from '@/components/Layout'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import RecordingsPage from '@/pages/RecordingsPage'
import RecordingDetailPage from '@/pages/RecordingDetailPage'
import TextTranslatePage from '@/pages/TextTranslatePage'
import VoiceTranslatePage from '@/pages/VoiceTranslatePage'
import DictionaryPage from '@/pages/DictionaryPage'
import SettingsPage from '@/pages/SettingsPage'
import SharedPage from '@/pages/SharedPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    return <>{children}</>
}

function App() {
    return (
        <Routes>
            <Route path="/login" element={<LoginPage />} />

            {/* Public route for shared content */}
            <Route path="/shared/:token" element={<SharedPage />} />

            <Route
                path="/"
                element={
                    <PrivateRoute>
                        <Layout />
                    </PrivateRoute>
                }
            >
                <Route index element={<DashboardPage />} />
                <Route path="recordings" element={<RecordingsPage />} />
                <Route path="recordings/:id" element={<RecordingDetailPage />} />
                <Route path="text-translate" element={<TextTranslatePage />} />
                <Route path="voice-translate" element={<VoiceTranslatePage />} />
                <Route path="voice-translate/:id" element={<RecordingDetailPage />} />
                <Route path="dictionary" element={<DictionaryPage />} />
                <Route path="settings/*" element={<SettingsPage />} />
            </Route>
        </Routes>
    )
}

export default App
