//
//  HomeView.swift
//  bounce
//
//  Created by Cameron Goodhue on 07/09/2025.
//


import SwiftUI

struct HomeView: View {
    @State private var showCreateBounce = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("Welcome to Bounce 👋")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Plan a hangout with friends, one at a time.")
                    .font(.subheadline)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                
                Spacer()
                
                Button(action: { showCreateBounce = true }) {
                    Text("Create Bounce")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                        .shadow(radius: 5)
                }
                .padding(.horizontal)
                
                Spacer()
            }
            .sheet(isPresented: $showCreateBounce) {
                CreateBounceView()
            }
            .navigationTitle("Bounce")
        }
    }
}

#Preview {
    HomeView()
}
