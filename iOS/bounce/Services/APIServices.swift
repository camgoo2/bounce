//
//  APIServices.swift
//  bounce
//
//  Created by Cameron Goodhue on 07/09/2025.
//

import Foundation

class APIService {
    static let shared = APIService()
    private let baseURL = URL(string: "http://127.0.0.1:8000")! // Update for production later

    func checkHealth(completion: @escaping (Result<[String: String], Error>) -> Void) {
        let url = baseURL.appendingPathComponent("health")
        
        URLSession.shared.dataTask(with: url) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            guard let data = data else {
                completion(.failure(NSError(domain: "", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"])))
                return
            }
            do {
                let result = try JSONSerialization.jsonObject(with: data) as? [String: String]
                completion(.success(result ?? [:]))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    func createBounce(title: String, date: Date, completion: @escaping (Result<Void, Error>) -> Void) {
        // Existing code remains unchanged
        let url = baseURL.appendingPathComponent("bounces")
        // ... rest of the method ...
    }
}
