"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { apiClient, type AnalyzeRequest } from "@/lib/api"
import Link from "next/link"
import { ArrowLeft, Download, Loader2 } from "lucide-react"

export default function AnalyzePage() {
  const [codebasePath, setCodebasePath] = useState("")
  const [mode, setMode] = useState("full")
  const [provider, setProvider] = useState("auto")
  const [analyzing, setAnalyzing] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (jobId && analyzing) {
      const interval = setInterval(async () => {
        try {
          const jobResult = await apiClient.getAnalyzeResult(jobId)
          if (jobResult.status === "completed") {
            setAnalyzing(false)
            setResult(jobResult.result)
            setProgress(100)
            clearInterval(interval)
          } else if (jobResult.status === "failed") {
            setAnalyzing(false)
            setError(jobResult.error || "Analysis failed")
            clearInterval(interval)
          } else {
            setProgress((prev) => Math.min(prev + 5, 90))
          }
        } catch (err) {
          console.error("Error checking job status:", err)
        }
      }, 2000)

      return () => clearInterval(interval)
    }
  }, [jobId, analyzing])

  const handleAnalyze = async () => {
    if (!codebasePath.trim()) {
      setError("Please enter a codebase path")
      return
    }

    setAnalyzing(true)
    setError(null)
    setResult(null)
    setProgress(0)

    try {
      const request: AnalyzeRequest = {
        codebase_path: codebasePath,
        mode,
        provider,
      }

      const response = await apiClient.analyze(request)
      setJobId(response.job_id)
      setProgress(10)
    } catch (err: any) {
      setAnalyzing(false)
      setError(err.message || "Failed to start analysis")
    }
  }

  const handleDownload = () => {
    if (!result) return

    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "analysis-result.json"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Analyze Codebase</h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Codebase Path</CardTitle>
                <CardDescription>Enter the path to the codebase directory to analyze</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Path</label>
                  <Input
                    placeholder="/path/to/codebase"
                    value={codebasePath}
                    onChange={(e) => setCodebasePath(e.target.value)}
                    disabled={analyzing}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Analysis Mode</label>
                  <Select value={mode} onValueChange={setMode} disabled={analyzing}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="full">Full Analysis</SelectItem>
                      <SelectItem value="systems">Systems Only</SelectItem>
                      <SelectItem value="holes">System Holes Only</SelectItem>
                      <SelectItem value="enhancements">Enhancements Only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Provider</label>
                  <Select value={provider} onValueChange={setProvider} disabled={analyzing}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Auto</SelectItem>
                      <SelectItem value="ollama">Ollama</SelectItem>
                      <SelectItem value="qwen">Qwen AI</SelectItem>
                      <SelectItem value="gemini">Google Gemini</SelectItem>
                      <SelectItem value="openrouter">OpenRouter</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button onClick={handleAnalyze} disabled={analyzing} className="w-full">
                  {analyzing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    "Analyze"
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            {analyzing && (
              <Card>
                <CardHeader>
                  <CardTitle>Progress</CardTitle>
                </CardHeader>
                <CardContent>
                  <Progress value={progress} className="mb-2" />
                  <p className="text-sm text-muted-foreground">Analyzing codebase... {progress}%</p>
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
                    Analysis Results
                    <Button onClick={handleDownload} variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="bg-muted p-4 rounded-md overflow-auto max-h-[600px] text-sm">
                    {JSON.stringify(result, null, 2)}
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

