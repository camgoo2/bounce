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
    @State private var friend: String = ""
    @State private var isSubmitting = false
    @State private var message: String?

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Details")) {
                    TextField("What's the plan?", text: $title)
                    DatePicker("When", selection: $date, displayedComponents: [.date, .hourAndMinute])
                    TextField("Invite a friend", text: $friend) // New TextField for friend
                }
                
                if let message = message {
                    Text(message)
                        .foregroundColor(message.contains("Error") ? .red : .green)
                }
                
                Button(action: submitBounce) {
                    if isSubmitting {
                        ProgressView()
                    } else {
                        Text("Send Bounce")
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(title.isEmpty || isSubmitting ? Color.gray : Color.blue)
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                }
                .disabled(title.isEmpty || isSubmitting)
            }
            .navigationTitle("Create Bounce")
        }
    }
    
    private func submitBounce() {
        isSubmitting = true
        APIService.shared.createBounce(title: title, date: date, friend: friend) { result in
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
