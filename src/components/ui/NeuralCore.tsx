"use client"

import React, { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { NeuralPacket } from '../../types/neural_protocol'

interface NeuralCoreProps {
  className?: string
  nodeCount?: number
  packet?: NeuralPacket | null
}

export function NeuralCore({ className, nodeCount = 200, packet }: NeuralCoreProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const packetRef = useRef<NeuralPacket | null>(null)

  useEffect(() => {
    packetRef.current = packet ?? null
  }, [packet])
  
  useEffect(() => {
    if (!containerRef.current) return

    // Scene Setup
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    containerRef.current.appendChild(renderer.domElement)

    // Particle Data
    const particles = new Float32Array(nodeCount * 3)
    const velocities = new Float32Array(nodeCount * 3)
    const particlePositions: THREE.Vector3[] = []
    
    // Synapse Pre-allocation (Spatial optimized scale)
    const MAX_SYNAPSES = nodeCount * 10
    const linePositions = new Float32Array(MAX_SYNAPSES * 6)

    for (let i = 0; i < nodeCount; i++) {
        const x = (Math.random() - 0.5) * 100
        const y = (Math.random() - 0.5) * 100
        const z = (Math.random() - 0.5) * 100
        particles[i * 3] = x
        particles[i * 3 + 1] = y
        particles[i * 3 + 2] = z
        
        velocities[i * 3] = (Math.random() - 0.5) * 0.1
        velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.1
        velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.1
        
        particlePositions.push(new THREE.Vector3(x, y, z))
    }

    // Nodes Geometry
    const nodeGeometry = new THREE.BufferGeometry()
    nodeGeometry.setAttribute('position', new THREE.BufferAttribute(particles, 3))
    
    // Dynamic Base Color
    const baseColor = new THREE.Color(0x10b981) // Default Emerald
    const stressedColor = new THREE.Color(0xef4444) // Stressed Crimson
    
    const nodeMaterial = new THREE.PointsMaterial({
        size: 0.2,
        color: baseColor,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    })
    
    const nodes = new THREE.Points(nodeGeometry, nodeMaterial)
    scene.add(nodes)

    // Synapses (Connections)
    const lineMaterial = new THREE.LineBasicMaterial({
        color: 0x6366f1, // Indigo-500
        transparent: true,
        opacity: 0.2,
        blending: THREE.AdditiveBlending
    })
    
    const lineGeometry = new THREE.BufferGeometry()
    const connections = new THREE.LineSegments(lineGeometry, lineMaterial)
    scene.add(connections)

    camera.position.z = 40

    // Interaction State
    let mouseX = 0
    let mouseY = 0
    let targetX = 0
    let targetY = 0

    const handleMouseMove = (event: MouseEvent) => {
        mouseX = (event.clientX - window.innerWidth / 2) / 100
        mouseY = (event.clientY - window.innerHeight / 2) / 100
    }

    window.addEventListener('mousemove', handleMouseMove)

    // Resize Handler
    const handleResize = () => {
        camera.aspect = window.innerWidth / window.innerHeight
        camera.updateProjectionMatrix()
        renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', handleResize)

    const startTime = performance.now()

    // Animation Loop
    const animate = () => {
        requestAnimationFrame(animate)
        
        // --- NEURAL MODULATION ---
        const p = packetRef.current
        const state = p?.state || "IDLE"
        
        
        // Dynamic Base Color based on System State
        const isAlertActive = !!p?.alert
        const targetColor = isAlertActive ? stressedColor : baseColor
        nodeMaterial.color.lerp(targetColor, 0.05)
        
        // 1. Particle Physics & Scaling Pulse
        const time = (performance.now() - startTime) / 1000
        const pulseScale = isAlertActive ? 1.0 + Math.sin(time * 5) * 0.2 : 1.0
        
        for (let i = 0; i < nodeCount; i++) {
            const i3 = i * 3
            // Speed up during alerts
            const speedFactor = isAlertActive ? 4.0 : 1.0
            
            particles[i3] += velocities[i3] * speedFactor
            particles[i3+1] += velocities[i3+1] * speedFactor
            particles[i3+2] += velocities[i3+2] * speedFactor

            // Neural Bounds
            if (Math.abs(particles[i3]) > 50) velocities[i3] *= -1
            if (Math.abs(particles[i3+1]) > 50) velocities[i3+1] *= -1
            if (Math.abs(particles[i3+2]) > 50) velocities[i3+2] *= -1

            particlePositions[i].set(particles[i3], particles[i3+1], particles[i3+2])
        }
        
        // Apply Pulse to Node Size
        nodeMaterial.size = (isAlertActive ? 0.4 : 0.2) * pulseScale
        nodeGeometry.attributes.position.needsUpdate = true

        // --- SPATIAL GRID OPTIMIZATION (Neural Scale 1.0) ---
        const grid: Map<string, number[]> = new Map()
        const cellSize = 12
        const maxDist = state === "THINKING" ? 18 : 12

        // 1. Binning
        for (let i = 0; i < nodeCount; i++) {
            const gx = Math.floor(particlePositions[i].x / cellSize)
            const gy = Math.floor(particlePositions[i].y / cellSize)
            const gz = Math.floor(particlePositions[i].z / cellSize)
            const key = `${gx},${gy},${gz}`
            if (!grid.has(key)) grid.set(key, [])
            grid.get(key)!.push(i)
        }

        // 2. Synapse Projection (O(N) lookup)
        let lineIdx = 0
        for (let i = 0; i < nodeCount; i++) {
            const gx = Math.floor(particlePositions[i].x / cellSize)
            const gy = Math.floor(particlePositions[i].y / cellSize)
            const gz = Math.floor(particlePositions[i].z / cellSize)

            // Check neighbors (27 cells)
            for (let ox = -1; ox <= 1; ox++) {
                for (let oy = -1; oy <= 1; oy++) {
                    for (let oz = -1; oz <= 1; oz++) {
                        const key = `${gx + ox},${gy + oy},${gz + oz}`
                        const cell = grid.get(key)
                        if (cell) {
                            for (const j of cell) {
                                if (i >= j) continue 
                                if (lineIdx >= MAX_SYNAPSES * 6) break

                                const distSq = particlePositions[i].distanceToSquared(particlePositions[j])
                                if (distSq < maxDist * maxDist) {
                                    linePositions[lineIdx++] = particlePositions[i].x
                                    linePositions[lineIdx++] = particlePositions[i].y
                                    linePositions[lineIdx++] = particlePositions[i].z
                                    linePositions[lineIdx++] = particlePositions[j].x
                                    linePositions[lineIdx++] = particlePositions[j].y
                                    linePositions[lineIdx++] = particlePositions[j].z
                                }
                            }
                        }
                    }
                }
            }
        }
        
        lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3))
        lineGeometry.setDrawRange(0, lineIdx / 3)
        lineGeometry.attributes.position.needsUpdate = true

        // Parallax Effect
        targetX += (mouseX - targetX) * 0.05
        targetY += (mouseY - targetY) * 0.05
        camera.position.x = targetX * 2
        camera.position.y = -targetY * 2
        camera.lookAt(scene.position)
        
        renderer.render(scene, camera)
    }

    animate()

    // Cleanup
    return () => {
        window.removeEventListener('mousemove', handleMouseMove)
        window.removeEventListener('resize', handleResize)
        if (containerRef.current) {
            containerRef.current.removeChild(renderer.domElement)
        }
        nodeGeometry.dispose()
        nodeMaterial.dispose()
        lineGeometry.dispose()
        lineMaterial.dispose()
        renderer.dispose()
    }
  }, [nodeCount]) // Do not recreate Three.js scene on every packet update

  return <div ref={containerRef} className={`${className} fixed inset-0 z-0 pointer-events-none`} />
}
