// Initialize customer profiles database
db = db.getSiblingDB('ecommerce');

// Create customer profiles collection with sample data
db.customer_profiles.insertMany([
  {
    _id: ObjectId(),
    customer_id: 1001,
    name: "Alice Johnson",
    email: "alice@example.com",
    demographics: {
      age: 28,
      location: "San Francisco, CA",
      income_bracket: "high"
    },
    preferences: {
      categories: ["electronics", "books"],
      communication: "email",
      loyalty_program: true
    },
    social_media: {
      platforms: ["instagram", "twitter"],
      influence_score: 75
    },
    created_at: new Date("2023-01-15"),
    updated_at: new Date("2025-01-01")
  },
  {
    _id: ObjectId(),
    customer_id: 1002,
    name: "Bob Smith",
    email: "bob@example.com",
    demographics: {
      age: 35,
      location: "New York, NY",
      income_bracket: "medium"
    },
    preferences: {
      categories: ["clothing", "sports"],
      communication: "sms",
      loyalty_program: false
    },
    social_media: {
      platforms: ["linkedin"],
      influence_score: 45
    },
    created_at: new Date("2023-03-20"),
    updated_at: new Date("2024-12-15")
  },
  {
    _id: ObjectId(),
    customer_id: 1003,
    name: "Carol Davis",
    email: "carol@example.com",
    demographics: {
      age: 42,
      location: "Chicago, IL",
      income_bracket: "high"
    },
    preferences: {
      categories: ["home", "electronics", "books"],
      communication: "email",
      loyalty_program: true
    },
    social_media: {
      platforms: ["facebook", "instagram"],
      influence_score: 85
    },
    created_at: new Date("2022-11-10"),
    updated_at: new Date("2024-11-30")
  },
  {
    _id: ObjectId(),
    customer_id: 1004,
    name: "David Wilson",
    email: "david@example.com",
    demographics: {
      age: 25,
      location: "Austin, TX",
      income_bracket: "low"
    },
    preferences: {
      categories: ["gaming", "electronics"],
      communication: "app",
      loyalty_program: false
    },
    social_media: {
      platforms: ["twitter", "tiktok", "instagram"],
      influence_score: 60
    },
    created_at: new Date("2024-02-05"),
    updated_at: new Date("2024-12-20")
  },
  {
    _id: ObjectId(),
    customer_id: 1005,
    name: "Eva Martinez",
    email: "eva@example.com",
    demographics: {
      age: 31,
      location: "Los Angeles, CA",
      income_bracket: "high"
    },
    preferences: {
      categories: ["beauty", "clothing", "home"],
      communication: "email",
      loyalty_program: true
    },
    social_media: {
      platforms: ["instagram", "pinterest", "facebook"],
      influence_score: 90
    },
    created_at: new Date("2023-07-12"),
    updated_at: new Date("2025-01-10")
  }
]);

// Create index for efficient querying
db.customer_profiles.createIndex({ customer_id: 1 });
db.customer_profiles.createIndex({ "demographics.income_bracket": 1 });
db.customer_profiles.createIndex({ "preferences.loyalty_program": 1 });

print("✅ Customer profiles collection initialized with sample data");