"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Sparkles, Code, Settings, Database, Home } from "lucide-react"
import { cn } from "@/lib/utils"

export function Navigation() {
  const pathname = usePathname()

  const navItems = [
    { href: "/", label: "Home", icon: Home },
    { href: "/generate", label: "Generate", icon: Sparkles },
    { href: "/analyze", label: "Analyze", icon: Code },
    { href: "/config", label: "Config", icon: Settings },
    { href: "/cache", label: "Cache", icon: Database },
  ]

  return (
    <nav className="border-b bg-card">
      <div className="container mx-auto px-4">
        <div className="flex items-center gap-2 h-16">
          <Link href="/" className="font-bold text-xl mr-4">
            MEGAPROMPT
          </Link>
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={isActive ? "default" : "ghost"}
                  className={cn("gap-2", !isActive && "text-muted-foreground")}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Button>
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

