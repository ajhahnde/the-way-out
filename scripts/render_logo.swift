import AppKit
import Foundation

/// Renders the project logo using the Orbitron font.
/// Usage: swift scripts/render_logo.swift

let text = "THE WAY OUT"
let fontName = "Orbitron"
let fontSize: CGFloat = 160
let kern = 8.0
let padding: CGFloat = 40

func render(color: NSColor, filename: String) {
    guard let font = NSFont(name: fontName, size: fontSize) else {
        print("Error: Font '\(fontName)' not found. Please install it first.")
        exit(1)
    }

    let attributes: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: color,
        .kern: kern
    ]

    let attributedString = NSAttributedString(string: text, attributes: attributes)
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

// Generate light mode logo (black text)
render(color: .black, filename: "logo_light.png")

// Generate dark mode logo (white text)
render(color: .white, filename: "logo_dark.png")
