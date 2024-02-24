from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import joinedload
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from datetime import datetime
import os
import shutil
from fastapi import FastAPI, File, HTTPException, Depends, Request, UploadFile , status
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Enum , Float , DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session , relationship
from enum import Enum as PythonEnum
from os.path import join as path_join

DATABASE_URL = "mysql+pymysql://root:9518@127.0.0.1:3307/vegetable_db"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(length=255), unique=True, index=True)
    password = Column(String(length=50))

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(length=255), index=True)
    email = Column(String(length=255), unique=True, index=True)
    phone_no = Column(String(length=10), unique=True, index=True)
    address = Column(String(length=255))
    password = Column(String(length=50))
    
    orders = relationship("CustomerOrder", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(length=255), index=True)
    
    items = relationship("Item", back_populates="category")

# Item status enum
class ItemStatus(str, PythonEnum):
    active = "active"
    deactive = "deactive"
    
# Item model
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(length=255), index=True)
    description = Column(String(length=255))
    quantity = Column(Float)
    image_path = Column(String(length=255))
    category_id = Column(Integer, ForeignKey("categories.id"))
    status = Column(Enum(ItemStatus), default=ItemStatus.active)

    category = relationship("Category", back_populates="items")
    orders = relationship("Order", back_populates="item")
    pack_sizes = relationship("PackSize", back_populates="item")

# Order model
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    customer_order_id = Column(Integer, ForeignKey("customer_orders.id"))  # Add this line
    quantity = Column(Float)
    unit_price = Column(Float)
    time_stamp = Column(DateTime, default=datetime.utcnow)
    
    item = relationship("Item", back_populates="orders")
    customer_order = relationship("CustomerOrder", back_populates="orders")

# CustomerOrder model
class CustomerOrder(Base):
    __tablename__ = "customer_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_amount = Column(Float)
    order_date = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="orders")
    orders = relationship("Order", back_populates="customer_order")
    
# Review model
class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String(length=255))
    time_stamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reviews")
    
# PackSize model
class PackSize(Base):
    __tablename__ = "pack_sizes"

    id = Column(Integer, primary_key=True, index=True)
    size = Column(Float)
    price = Column(Float)
    item_id = Column(Integer, ForeignKey("items.id"))

    item = relationship("Item", back_populates="pack_sizes")


Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# Add the following line at the beginning of your FastAPI app to mount the image directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to the specific origin(s) you want to allow
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        # print(db)
        yield db
    finally:
        db.close()
        
# Email format validation
def is_valid_email(email: str):
    return "@" in email

# Admin Sign In
@app.post("/admin/login")
def admin_login(email: str, password: str, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == email, Admin.password == password).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    admin_id = admin.id
    
    raise HTTPException(
        status_code=status.HTTP_200_OK,
        detail={"status": status.HTTP_200_OK,"message": "Login Successfully", "admin_id": admin_id})
    
# Sign Up
@app.post("/signup", response_model=dict)
def signup(name: str, email: str, phone_no: str, address: str, password: str, db: Session = Depends(get_db)):
    
    # Check email format
    if not is_valid_email(email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"status": status.HTTP_422_UNPROCESSABLE_ENTITY, "message": "Invalid email format"},
        )
    
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(name=name, email=email, phone_no=phone_no,address=address, password=password)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    # return user
    raise HTTPException(
        status_code=status.HTTP_200_OK,
        detail={"status": status.HTTP_200_OK,"message": "Regestration Successfully"})

# Sign In
@app.post("/signin")
def signin(email: str, password: str, db: Session = Depends(get_db)):
    
    # Check email format
    if not is_valid_email(email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"status": status.HTTP_422_UNPROCESSABLE_ENTITY, "message": "Invalid email format"},
        )
    
    user = db.query(User).filter(User.email == email, User.password == password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id = user.id

    raise HTTPException(
        status_code=status.HTTP_200_OK,
        detail={"status": status.HTTP_200_OK,"message": "Login Successfully", "user_id": user_id})

# Create Category
@app.post("/categories/", response_model=None)
def create_category(name: str, db: Session = Depends(get_db)):
    
    category = Category(name=name)
    
    db.add(category)
    db.commit()
    db.refresh(category)
    return {"message": "Category created successfully"}

# Update Category
@app.put("/categories/{category_id}", response_model=dict)
def update_category(category_id: int, name: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    category.name = name
    db.commit()
    db.refresh(category)
    return {"message": "Category updated successfully"}

# Delete Category
@app.delete("/categories/{category_id}", response_model=dict)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}

# Get all categories
@app.get("/categories/", response_model=dict)
def get_all_categories(db: Session = Depends(get_db)):
    
    categories = db.query(Category).all()
    return jsonable_encoder({"message": "Categories retrieved successfully", "categories": categories})

# Create Item
@app.post("/items/", response_model=dict)
def create_item(
    name: str,
    description: str,
    quantity: float,
    category_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Save the image to a directory on the server
    upload_path = "uploads"
    os.makedirs(upload_path, exist_ok=True)
    image_path = os.path.join(upload_path, image.filename)

    with open(image_path, "wb") as file:
        shutil.copyfileobj(image.file, file)

    item = Item(name=name, description=description, quantity=quantity, category_id=category_id, image_path=image_path)

    db.add(item)
    db.commit()
    db.refresh(item)

    return {"message": "Item created successfully"}
    # return jsonable_encoder({"message": "Item created successfully", "item": item})

# Update Item
@app.put("/items/{item_id}", response_model=dict)
def update_item(
    item_id: int,
    name: str,
    description: str,
    quantity: int,
    category_id: int,
    status: Optional[ItemStatus] = None,
    image_path: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # try:
        # Retrieve the existing item from the database
        item = db.query(Item).filter(Item.id == item_id).first()

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Update the item properties
        item.name = name
        item.description = description
        item.quantity = quantity
        item.category_id = category_id
        
        # Update the item status if provided
        if status is not None:
            item.status = status

        # Save the updated image if provided
        if image_path:
            upload_path = "uploads"
            os.makedirs(upload_path, exist_ok=True)
            new_image_path = os.path.join(upload_path, image_path.filename)

            with open(new_image_path, "wb") as file:
                shutil.copyfileobj(image_path.file, file)

            item.image_path = new_image_path

        db.commit()
        db.refresh(item)

        return {"message": "Item updated successfully"}
    # except Exception as e:
    #     # Handle any potential exceptions, log or return an appropriate response
    #     raise HTTPException(status_code=500, detail=str(e))
    
# Delete Item
@app.delete("/items/{item_id}", response_model=dict)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # Delete the associated image from the "uploads" folder
    if item.image_path:
        image_path = os.path.join("uploads", os.path.basename(item.image_path))
        try:
            os.remove(image_path)
            print("Image deleted successfully")
        except Exception as e:
            print(f"Error deleting image: {str(e)}")

    db.delete(item)
    db.commit()
    return {"message": "Item deleted successfully"}

# Get all Items
@app.get("/items/", response_model=dict)
def get_all_items(db: Session = Depends(get_db)):
    items = db.query(Item).all()
    
    # Create a list to store items with category name
    items_with_category = []
    
    for item in items:
        # Get the category name for each item
        category_name = db.query(Category.name).filter(Category.id == item.category_id).first()[0]
        
         # Construct the image URL
        image_url = path_join("/", item.image_path.replace("\\", "/"))

        
        # Convert the item to a dictionary and include the category name
        item_dict = {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "quantity": item.quantity,
            "image_path": image_url,
            # "image_path": item.image_path,
            "category_id": item.category_id,
            "status": item.status,
            "category_name": category_name  # Include the category name in the response
        }
        
        items_with_category.append(item_dict)

    return jsonable_encoder({"message": "Items retrieved successfully", "items": items_with_category})

# Create Order
@app.post("/orders/", response_model=dict)
def create_order(
    item_id: List[int],
    quantity: List[float],
    unit_price: List[float],
    user_id: int,
    total_amount: float,
    db: Session = Depends(get_db)
):
    # Check if the length of item_id, quantity, and unit_price lists is the same
    if len(item_id) != len(quantity) or len(quantity) != len(unit_price):
        raise HTTPException(status_code=400, detail="Invalid input data")

    # Create a CustomerOrder
    customer_order = CustomerOrder(user_id=user_id, total_amount=total_amount)
    db.add(customer_order)
    db.commit()
    db.refresh(customer_order)

    # Create Orders for each item in the order
    for i in range(len(item_id)):
        item = db.query(Item).filter(Item.id == item_id[i]).first()
        if item is None or item.quantity < quantity[i]:
            raise HTTPException(status_code=400, detail=f"Insufficient quantity for item {item_id[i]}")

        # Update item quantity
        item.quantity -= quantity[i]

        order = Order(
            item_id=item_id[i],
            quantity=quantity[i],
            unit_price=unit_price[i],
            customer_order_id=customer_order.id
        )
        db.add(order)
        db.commit()

    return {"message": "Order created successfully"}

# Cancel Order by Customer Order ID
@app.delete("/orders/{customer_order_id}", response_model=dict)
def cancel_order(customer_order_id: int, db: Session = Depends(get_db)):
    # Retrieve the customer order from the database
    customer_order = db.query(CustomerOrder).filter(CustomerOrder.id == customer_order_id).first()

    if customer_order is None:
        raise HTTPException(status_code=404, detail=f"Customer order ID not found")

    # Add back the quantities of the cancelled items to the respective items
    for order in customer_order.orders:
        item = db.query(Item).filter(Item.id == order.item_id).first()
        if item:
            item.quantity += order.quantity
            
    # Delete associated orders
    db.query(Order).filter(Order.customer_order_id == customer_order_id).delete()

    # Delete the customer order and associated orders
    db.delete(customer_order)
    db.commit()

    return {"message": f"Order cancelled successfully"}

# Get all orders
@app.get("/orders/", response_model=dict)
def get_all_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return jsonable_encoder({"message": "Orders retrieved successfully", "orders": orders})

# Get orders by user ID
@app.get("/orders/{user_id}", response_model=dict)
def get_orders_by_user_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    orders = (
        db.query(CustomerOrder)
        .options(joinedload(CustomerOrder.orders).joinedload(Order.item))
        .filter(CustomerOrder.user_id == user_id)
        .all()
    )

    formatted_orders = []
    for order in orders:
        order_info = {
            "order_date": order.order_date,
            "total_amount": order.total_amount,
            "items": [
                {
                    "item_name": order_item.item.name,
                    "quantity": order_item.quantity,
                    "unit_price": order_item.unit_price,
                }
                for order_item in order.orders
            ],
        }
        formatted_orders.append(order_info)

    return jsonable_encoder({"message": "Orders retrieved successfully", "orders": formatted_orders})

# Add Review
@app.post("/add_review/", response_model=dict)
def add_review(
    user_id: int,
    text: str,
    db: Session = Depends(get_db)
):
    review = Review(user_id=user_id, text=text)
    db.add(review)
    db.commit()
    db.refresh(review)

    return {"message": "Review added successfully"}

# Get All Reviews
@app.get("/get_all_reviews/", response_model=dict)
def get_all_reviews(db: Session = Depends(get_db)):
    reviews = db.query(Review).all()
    return jsonable_encoder({"message": "Reviews retrieved successfully", "reviews": reviews})

# Create Pack Size
@app.post("/pack_sizes/", response_model=dict)
def create_pack_size(
    item_id: int,
    size: float,
    price: float,
    db: Session = Depends(get_db)
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    pack_size = PackSize(size=size, price=price, item_id=item_id)
    
    db.add(pack_size)
    db.commit()
    db.refresh(pack_size)

    return {"message": "Pack size created successfully"}

# Get Pack Sizes for an Item
@app.get("/pack_sizes/{item_id}", response_model=dict)
def get_pack_sizes(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    pack_sizes = db.query(PackSize).filter(PackSize.item_id == item_id).all()
    
    return jsonable_encoder({"message": f"Pack sizes for Item {item_id} retrieved successfully", "pack_sizes": pack_sizes})

# Delete Pack Size by ID
@app.delete("/pack_sizes/{pack_size_id}", response_model=dict)
def delete_pack_size(pack_size_id: int, db: Session = Depends(get_db)):
    pack_size = db.query(PackSize).filter(PackSize.id == pack_size_id).first()
    if pack_size is None:
        raise HTTPException(status_code=404, detail="Pack size not found")

    db.delete(pack_size)
    db.commit()

    return {"message": "Pack size deleted successfully"}

# Get All Pack Sizes
@app.get("/get_all_pack_sizes/", response_model=dict)
def get_all_pack_sizes(db: Session = Depends(get_db)):
    all_pack_sizes = (
        db.query(PackSize, Item.name)
        .join(Item, PackSize.item_id == Item.id)
        .all()
    )

    formatted_pack_sizes = [
        {
            "pack_size_id": pack_size.id,
            "size": pack_size.size,
            "price": pack_size.price,
            "item_id": pack_size.item_id,
            "item_name": item_name,
        }
        for pack_size, item_name in all_pack_sizes
    ]

    return jsonable_encoder({"message": "All pack sizes retrieved successfully", "all_pack_sizes": formatted_pack_sizes})
