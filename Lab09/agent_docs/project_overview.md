# Project Overview

## Purpose

Implement the upload-speed exercise in `Laboratorio_-_SpeedTest.pdf`. A Linux
Python client constructs IPv4/TCP packets and uploads ten copies of a 1000-byte
binary file in one connection to a separate receiver that uses the OS TCP stack.

## Scope and Architecture

The client measures the opening handshake and each file's data confirmation,
then reports the PDF's educational speed estimate and can write ten samples to
CSV. The receiver validates the complete TCP byte stream and saves the upload.
This is a focused IPv4 upload exercise, not a general TCP implementation; see
the [README](../README.md) for execution details and limitations.

## Main Workflows

The Makefile provides syntax checking, unit tests, an isolated raw-TCP
integration run, and ZIP packaging. The README is the canonical guide for
commands, permissions, capture, and delivery.

## Major Decisions

- Use Python's standard library on Linux, as permitted by the assignment, with
  a separate binary receiver rather than reusing the text-based Lab01 service.
- Treat 1 KB as 1000 bytes to match the PDF's numerical example; send all ten
  copies over one connection.
- Keep the PDF estimate as an exercise metric, not a claim about maximum link
  capacity. Incoming TCP checksum validation and the one-second close wait have
  documented platform and protocol limitations.
