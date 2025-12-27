"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Sparkles, Code, Settings, Database } from "lucide-react"

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Dashboard</h1>
          <p className="text-muted-foreground text-lg">
            Transform messy prompts into structured, deterministic mega-prompts
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Generate Mega-Prompt
              </CardTitle>
              <CardDescription>
                Transform your ideas into structured mega-prompts through a 5-stage pipeline
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/generate">
                <Button className="w-full">Start Generating</Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                Analyze Codebase
              </CardTitle>
              <CardDescription>
                Identify system holes, architectural risks, and enhancement opportunities
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/analyze">
                <Button className="w-full" variant="secondary">Start Analysis</Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Configuration
              </CardTitle>
              <CardDescription>
                Manage LLM provider settings, API keys, and preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/config">
                <Button className="w-full" variant="outline">Configure</Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Cache & Checkpoints
              </CardTitle>
              <CardDescription>
                View cache statistics and manage checkpoints from previous runs
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/cache">
                <Button className="w-full" variant="outline">Manage</Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>About MEGAPROMPT</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              MEGAPROMPT uses a 5-stage pipeline to transform messy human prompts into structured,
              deterministic mega-prompts optimized for AI execution:
            </p>
            <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
              <li>Intent Extraction - Removes fluff, extracts core intent</li>
              <li>Project Decomposition - Breaks project into orthogonal systems</li>
              <li>Domain Expansion - Expands each system with detailed specifications</li>
              <li>Risk Analysis - Identifies unknowns and risk points</li>
              <li>Constraint Enforcement - Applies technical constraints</li>
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

