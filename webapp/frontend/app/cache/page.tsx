"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { apiClient } from "@/lib/api"
import Link from "next/link"
import { ArrowLeft, RefreshCw, Trash2, Loader2, Database, Clock } from "lucide-react"

export default function CachePage() {
  const [cacheStats, setCacheStats] = useState<any>(null)
  const [checkpoints, setCheckpoints] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [clearing, setClearing] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [cacheData, checkpointsData] = await Promise.all([
        apiClient.getCacheStats(),
        apiClient.getCheckpoints(),
      ])
      setCacheStats(cacheData)
      setCheckpoints(checkpointsData.checkpoints || [])
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to load data" })
    } finally {
      setLoading(false)
    }
  }

  const handleClearCache = async () => {
    if (!confirm("Are you sure you want to clear the cache? This cannot be undone.")) {
      return
    }

    setClearing(true)
    setMessage(null)

    try {
      await apiClient.clearCache()
      setMessage({ type: "success", text: "Cache cleared successfully" })
      loadData()
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to clear cache" })
    } finally {
      setClearing(false)
    }
  }

  const handleDeleteCheckpoint = async (id: string) => {
    if (!confirm(`Are you sure you want to delete checkpoint ${id}?`)) {
      return
    }

    try {
      await apiClient.deleteCheckpoint(id)
      setMessage({ type: "success", text: "Checkpoint deleted successfully" })
      loadData()
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to delete checkpoint" })
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
        <h1 className="text-3xl font-bold mb-6">Cache & Checkpoints</h1>

        {message && (
          <Alert variant={message.type === "error" ? "destructive" : "default"} className="mb-6">
            <AlertTitle>{message.type === "error" ? "Error" : "Success"}</AlertTitle>
            <AlertDescription>{message.text}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Cache Statistics
                </span>
                <div className="flex gap-2">
                  <Button onClick={loadData} variant="outline" size="sm">
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                  <Button onClick={handleClearCache} variant="destructive" size="sm" disabled={clearing}>
                    {clearing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </CardTitle>
              <CardDescription>View cache statistics and manage cached results</CardDescription>
            </CardHeader>
            <CardContent>
              {cacheStats ? (
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Cache Directory:</span>
                    <span className="font-mono text-sm">{cacheStats.cache_dir}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Exists:</span>
                    <Badge variant={cacheStats.exists ? "default" : "secondary"}>
                      {cacheStats.exists ? "Yes" : "No"}
                    </Badge>
                  </div>
                  {cacheStats.exists && (
                    <>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">File Count:</span>
                        <span>{cacheStats.file_count || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total Size:</span>
                        <span>{cacheStats.total_size_mb?.toFixed(2) || "0.00"} MB</span>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground">No cache statistics available</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Checkpoints
              </CardTitle>
              <CardDescription>View and manage checkpoints from previous generation runs</CardDescription>
            </CardHeader>
            <CardContent>
              {checkpoints.length > 0 ? (
                <div className="space-y-2">
                  {checkpoints.map((checkpoint) => (
                    <div
                      key={checkpoint.id}
                      className="flex items-center justify-between p-3 border rounded-md"
                    >
                      <div>
                        <p className="font-medium">{checkpoint.filename}</p>
                        <p className="text-sm text-muted-foreground">
                          {new Date(checkpoint.timestamp * 1000).toLocaleString()}
                        </p>
                      </div>
                      <Button
                        onClick={() => handleDeleteCheckpoint(checkpoint.id)}
                        variant="destructive"
                        size="sm"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No checkpoints found</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

