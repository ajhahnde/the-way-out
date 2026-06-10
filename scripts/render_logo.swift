import AppKit
import Foundation

/// Renders the project logo using the Orbitron font: neutral "THE WAY " in
/// the theme ink, accent "OUT" in the exit green (emerald — mid #10B981 on
/// light backgrounds, bright #34D399 on dark).
/// Usage: swift scripts/render_logo.swift

let fontName = "Orbitron"
let fontSize: CGFloat = 160
let kern = 8.0
let padding: CGFloat = 40

func color(_ hex: UInt32) -> NSColor {
    NSColor(srgbRed: CGFloat((hex >> 16) & 0xff) / 255.0,
            green: CGFloat((hex >> 8) & 0xff) / 255.0,
            blue: CGFloat(hex & 0xff) / 255.0,
            alpha: 1.0)
}

func render(neutral: NSColor, accent: NSColor, filename: String) {
    guard let font = NSFont(name: fontName, size: fontSize) else {
        print("Error: Font '\(fontName)' not found. Please install it first.")
        exit(1)
    }

    let attributedString = NSMutableAttributedString()
    attributedString.append(NSAttributedString(
        string: "THE WAY ",
        attributes: [.font: font, .foregroundColor: neutral, .kern: kern]))
    attributedString.append(NSAttributedString(
        string: "OUT",
        attributes: [.font: font, .foregroundColor: accent, .kern: kern]))

    let textSize = attributedString.size()
    let imageSize = NSSize(width: textSize.width + padding * 2, height: textSize.height + padding * 2)

    let image = NSImage(size: imageSize)
    image.lockFocus()

    // Draw text with optical centering adjustment if needed,
    // but here we just use the padding.
    attributedString.draw(at: NSPoint(x: padding, y: padding))

    image.unlockFocus()

    guard let tiffData = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiffData),
          let pngData = bitmap.representation(using: .png, properties: [:]) else {
        print("Error: Failed to generate PNG data for \(filename)")
        return
    }

    let url = URL(fileURLWithPath: "assets/\(filename)")
    do {
        try pngData.write(to: url)
        print("✓ Generated assets/\(filename)")
    } catch {
        print("Error: Failed to write \(filename): \(error)")
    }
}

// Light mode: ink #1a1a1a + emerald mid #10B981
render(neutral: color(0x1a1a1a), accent: color(0x10B981), filename: "logo_light.png")

// Dark mode: ink #f5f5f5 + emerald bright #34D399
render(neutral: color(0xf5f5f5), accent: color(0x34D399), filename: "logo_dark.png")
