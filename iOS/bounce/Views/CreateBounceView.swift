//
//  CreateBounceView.swift
//  bounce
//
//  Created by Cameron Goodhue on 07/09/2025.
//


import SwiftUI

struct CreateBounceView: View {
    @State private var title: String = ""
    @State private var date = Date()
    @State private var isSubmitting = false
    @State private var message: String?

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Details")) {
                    TextField("What's the plan?", text: $title)
                    DatePicker("When", selection: $date, displayedComponents: [.date, .hourAndMinute])
                }
                
                if let message = message {
                    Text(message)
                        .foregroundColor(.green)
                }
                
                Button(action: submitBounce) {
                    if isSubmitting {
                        ProgressView()
                    } else {
                        Text("Send Bounce")
                    }
                }
                .disabled(title.isEmpty || isSubmitting)
            }
            .navigationTitle("Create Bounce")
        }
    }
    
    private func submitBounce() {
        isSubmitting = true
        APIService.shared.createBounce(title: title, date: date) { result in
            DispatchQueue.main.async {
                isSubmitting = false
                switch result {
                case .success:
                    message = "Bounce created 🎉"
                    title = ""
                case .failure(let error):
                    message = "Error: \(error.localizedDescription)"
                }
            }
        }
    }
}
