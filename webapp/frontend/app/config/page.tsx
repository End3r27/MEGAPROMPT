"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { apiClient, type Config } from "@/lib/api"
import Link from "next/link"
import { ArrowLeft, Save, Loader2 } from "lucide-react"

export default function ConfigPage() {
  const [config, setConfig] = useState<Config>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const currentConfig = await apiClient.getConfig()
      setConfig(currentConfig)
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to load configuration" })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)

    try {
      await apiClient.updateConfig(config)
      setMessage({ type: "success", text: "Configuration saved successfully" })
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to save configuration" })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Configuration</h1>

        <Card>
          <CardHeader>
            <CardTitle>LLM Provider Settings</CardTitle>
            <CardDescription>
              Configure your LLM provider, API keys, and other settings. Configuration is loaded from:
              CLI arguments (highest priority) → Project config → User config → Defaults
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Provider</label>
              <Select
                value={config.provider || "auto"}
                onValueChange={(value) => setConfig({ ...config, provider: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto (Auto-detect)</SelectItem>
                  <SelectItem value="ollama">Ollama</SelectItem>
                  <SelectItem value="qwen">Qwen AI</SelectItem>
                  <SelectItem value="gemini">Google Gemini</SelectItem>
                  <SelectItem value="openrouter">OpenRouter</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Model (optional)</label>
              <Input
                placeholder="Leave empty for default"
                value={config.model || ""}
                onChange={(e) => setConfig({ ...config, model: e.target.value || undefined })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Temperature</label>
              <Input
                type="number"
                step="0.1"
                value={config.temperature?.toString() || "0.0"}
                onChange={(e) =>
                  setConfig({ ...config, temperature: parseFloat(e.target.value) || 0.0 })
                }
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">API Key (optional)</label>
              <Input
                type="password"
                placeholder="Uses environment variables if empty"
                value={config.api_key || ""}
                onChange={(e) => setConfig({ ...config, api_key: e.target.value || undefined })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Base URL (optional)</label>
              <Input
                placeholder="Provider-specific base URL"
                value={config.base_url || ""}
                onChange={(e) => setConfig({ ...config, base_url: e.target.value || undefined })}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Output Format</label>
              <Select
                value={config.output_format || "markdown"}
                onValueChange={(value) => setConfig({ ...config, output_format: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="markdown">Markdown</SelectItem>
                  <SelectItem value="json">JSON</SelectItem>
                  <SelectItem value="yaml">YAML</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {message && (
              <Alert variant={message.type === "error" ? "destructive" : "default"}>
                <AlertTitle>{message.type === "error" ? "Error" : "Success"}</AlertTitle>
                <AlertDescription>{message.text}</AlertDescription>
              </Alert>
            )}

            <Button onClick={handleSave} disabled={saving} className="w-full">
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Configuration
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

