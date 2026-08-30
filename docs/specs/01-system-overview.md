# OmniAssist System Specification: 01 System Overview

## Mission Statement
OmniAssist is an intelligent, low-latency, cross-platform desktop automation assistant designed to capture on-screen contextual queries, synthesize verified code or text solutions via multimodal LLMs, and deliver validated answers directly into the active editor or communication tool with zero workflow friction.

## Core Pillars
1. **Zero Data Loss**: Answers are never discarded upon delivery failure; automatic fallback to clipboard and HUD storage.
2. **Context-Aware Capture**: Hybrid capture pipeline supporting active selection, Accessibility Tree (AX), Tesseract OCR, and Multimodal Vision.
3. **Rigorous Validation**: Built-in AST syntax verification for code languages and auto-repair mechanisms for structured JSON.
4. **Resilient Recovery**: Standardized 15-category error classification with bounded jittered exponential backoff.
