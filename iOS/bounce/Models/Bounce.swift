//
//  Bounce.swift
//  bounce
//
//  Created by Cameron Goodhue on 07/09/2025.
//

import Foundation

struct Bounce: Codable, Identifiable {
    let id: UUID
    let title: String
    let date: Date
    
    // Optional: helper to format date for display
    var formattedDate: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

// Sample data for previews / testing UI without backend
extension Bounce {
    static let sampleData: [Bounce] = [
        Bounce(id: UUID(), title: "Driving Range at 4pm", date: Date().addingTimeInterval(3600)),
        Bounce(id: UUID(), title: "Coffee Hangout", date: Date().addingTimeInterval(7200))
    ]
}
