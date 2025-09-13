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
    
    func createBounce(title: String, date: Date, friend: String, completion: @escaping (Result<Void, Error>) -> Void) {
        let url = baseURL.appendingPathComponent("bounces")
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Format date as ISO 8601 string (or adjust to your API's expected format)
        let formatter = ISO8601DateFormatter()
        let dateString = formatter.string(from: date)
        
        // Create the request body
        let body: [String: Any] = [
            "title": title,
            "date": dateString,
            "friend": friend
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        } catch {
            completion(.failure(error))
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
                let statusCode = (response as? HTTPURLResponse)?.statusCode ?? -1
                let error = NSError(domain: "", code: statusCode, userInfo: [NSLocalizedDescriptionKey: "Invalid response from server"])
                completion(.failure(error))
                return
            }
            
            // If the API returns no data or just a success status, we return .success(())
            completion(.success(()))
        }.resume()
    }
}
