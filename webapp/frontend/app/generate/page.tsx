"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { apiClient, type GenerateRequest } from "@/lib/api"
import Link from "next/link"
import { ArrowLeft, Download, Loader2 } from "lucide-react"

export default function GeneratePage() {
  const [prompt, setPrompt] = useState("")
  const [provider, setProvider] = useState("auto")
  const [model, setModel] = useState("")
  const [temperature, setTemperature] = useState("0.0")
  const [apiKey, setApiKey] = useState("")
  const [outputFormat, setOutputFormat] = useState("markdown")
  const [generating, setGenerating] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (jobId && generating) {
      const interval = setInterval(async () => {
        try {
          const jobResult = await apiClient.getGenerateResult(jobId)
          if (jobResult.status === "completed") {
            setGenerating(false)
            setResult(jobResult.result || "")
            setProgress(100)
            clearInterval(interval)
          } else if (jobResult.status === "failed") {
            setGenerating(false)
            setError(jobResult.error || "Generation failed")
            clearInterval(interval)
          } else {
            // Update progress (simplified - in real implementation, use WebSocket)
            setProgress((prev) => Math.min(prev + 5, 90))
          }
        } catch (err) {
          console.error("Error checking job status:", err)
        }
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [jobId, generating])

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError("Please enter a prompt")
      return
    }

    setGenerating(true)
    setError(null)
    setResult(null)
    setProgress(0)

    try {
      const request: GenerateRequest = {
        prompt,
        provider,
        model: model || undefined,
        temperature: parseFloat(temperature) || 0.0,
        api_key: apiKey || undefined,
        output_format: outputFormat,
        verbose: true,
      }

      const response = await apiClient.generate(request)
      setJobId(response.job_id)
      setProgress(10)
    } catch (err: any) {
      setGenerating(false)
      setError(err.message || "Failed to start generation")
    }
  }

  const handleDownload = () => {
    if (!result) return

    const blob = new Blob([result], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `megaprompt-output.${outputFormat === "markdown" ? "md" : outputFormat}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Generate Mega-Prompt</h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Input Prompt</CardTitle>
                <CardDescription>Enter your prompt to transform into a structured mega-prompt</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  placeholder="Enter your prompt here..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={10}
                  disabled={generating}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Configuration</CardTitle>
                <CardDescription>Configure LLM provider and settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Provider</label>
                  <Select value={provider} onValueChange={setProvider} disabled={generating}>
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
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    disabled={generating}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Temperature</label>
                  <Input
                    type="number"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(e.target.value)}
                    disabled={generating}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">API Key (optional)</label>
                  <Input
                    type="password"
                    placeholder="Uses environment variables if empty"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    disabled={generating}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Output Format</label>
                  <Select value={outputFormat} onValueChange={setOutputFormat} disabled={generating}>
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

                <Button onClick={handleGenerate} disabled={generating} className="w-full">
                  {generating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    "Generate"
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            {generating && (
              <Card>
                <CardHeader>
                  <CardTitle>Progress</CardTitle>
                </CardHeader>
                <CardContent>
                  <Progress value={progress} className="mb-2" />
                  <p className="text-sm text-muted-foreground">Generating mega-prompt... {progress}%</p>
                </CardContent>
              </Card>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {result && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    Output
                    <Button onClick={handleDownload} variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="bg-muted p-4 rounded-md overflow-auto max-h-[600px] text-sm">
                    {result}
                  </pre>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

