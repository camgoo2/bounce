//
//  APIServices.swift
//  bounce
//
//  Created by Cameron Goodhue on 07/09/2025.
//

import Foundation

class APIService {
    static let shared = APIService()
    private let baseURL = URL(string: "http://127.0.0.1:8000")! // FastAPI placeholder
    
    func createBounce(title: String, date: Date, completion: @escaping (Result<Void, Error>) -> Void) {
        let url = baseURL.appendingPathComponent("bounces")
        
        let payload: [String: Any] = [
            "title": title,
            "date": ISO8601DateFormatter().string(from: date)
        ]
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        
        URLSession.shared.dataTask(with: request) { _, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            completion(.success(()))
        }.resume()
    }
}
