import streamlit as st
import boto3
import json
import base64
import io
from PIL import Image
import time
from datetime import datetime
import pandas as pd
import plotly.express as px

# Page config
st.set_page_config(page_title="AI Image Generator", page_icon="🎨", layout="wide")

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []
if "user_role" not in st.session_state:
    st.session_state.user_role = "user"

# Content filter
BLOCKED_WORDS = ["violence", "nude", "weapon", "hate", "illegal", "blood"]

def is_safe_prompt(prompt):
    """Check if prompt is safe"""
    return not any(word in prompt.lower() for word in BLOCKED_WORDS)

def generate_image_sagemaker(prompt, endpoint_name="stable-diffusion-endpoint"):
    """Generate image using SageMaker"""
    try:
        # Initialize SageMaker client
        client = boto3.client('sagemaker-runtime', region_name='us-east-1')
        
        # Prepare payload
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
                "width": 512,
                "height": 512
            }
        }
        
        # Call endpoint
        response = client.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        
        # Decode image
        if 'generated_images' in result:
            image_data = base64.b64decode(result['generated_images'][0])
            return Image.open(io.BytesIO(image_data))
        
        return None
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def create_demo_image():
    """Create demo image (for testing without SageMaker)"""
    time.sleep(2)  # Simulate processing
    return Image.new('RGB', (512, 512), color='lightblue')

# Main app
st.title("🎨 AI Image Generator")
st.write("Generate images from text descriptions using AI")

# Sidebar for navigation
tab = st.sidebar.radio("Navigation", ["🎨 Generate", "📊 Analytics", "ℹ️ Help"])

if tab == "🎨 Generate":
    # User role selection (simplified auth)
    role = st.selectbox("User Role", ["user", "admin", "viewer"])
    st.session_state.user_role = role
    
    if role == "viewer":
        st.warning("Viewers cannot generate images")
    else:
        # Generation form
        with st.form("generate_form"):
            prompt = st.text_area("Describe your image:", 
                                placeholder="A beautiful sunset over mountains")
            
            col1, col2 = st.columns(2)
            with col1:
                quality = st.slider("Quality", 1, 10, 7)
            with col2:
                use_demo = st.checkbox("Use demo mode", value=True, 
                                     help="Check this for demo without SageMaker")
            
            submitted = st.form_submit_button("Generate Image")
        
        if submitted and prompt:
            # Safety check
            if not is_safe_prompt(prompt):
                st.error("❌ Content blocked - prompt contains inappropriate content")
                # Log blocked attempt
                st.session_state.history.append({
                    "timestamp": datetime.now(),
                    "prompt": prompt,
                    "status": "blocked",
                    "role": role
                })
            else:
                # Generate image
                with st.spinner("Generating image..."):
                    start_time = time.time()
                    
                    if use_demo:
                        image = create_demo_image()
                    else:
                        image = generate_image_sagemaker(prompt)
                    
                    generation_time = time.time() - start_time
                
                if image:
                    # Display result
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.image(image, caption="Generated Image")
                    
                    with col2:
                        st.success("✅ Image generated!")
                        st.write(f"⏱️ Time: {generation_time:.1f}s")
                        st.write(f"📐 Size: 512x512")
                        
                        # Download button
                        img_buffer = io.BytesIO()
                        image.save(img_buffer, format="PNG")
                        img_buffer.seek(0)
                        
                        st.download_button(
                            "📥 Download",
                            data=img_buffer,
                            file_name=f"generated_{int(time.time())}.png",
                            mime="image/png"
                        )
                    
                    # Log successful generation
                    st.session_state.history.append({
                        "timestamp": datetime.now(),
                        "prompt": prompt,
                        "status": "success",
                        "time": generation_time,
                        "role": role
                    })
                else:
                    st.error("❌ Failed to generate image")
                    st.session_state.history.append({
                        "timestamp": datetime.now(),
                        "prompt": prompt,
                        "status": "failed",
                        "role": role
                    })

elif tab == "📊 Analytics":
    st.subheader("📊 Usage Analytics")
    
    if not st.session_state.history:
        st.info("No generation history yet")
    else:
        # Summary metrics
        total = len(st.session_state.history)
        successful = sum(1 for h in st.session_state.history if h["status"] == "success")
        blocked = sum(1 for h in st.session_state.history if h["status"] == "blocked")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Requests", total)
        col2.metric("Successful", successful)
        col3.metric("Blocked", blocked)
        
        # Charts
        if total > 0:
            # Status distribution
            status_counts = {"Success": successful, "Failed": total - successful - blocked, "Blocked": blocked}
            fig = px.pie(values=list(status_counts.values()), names=list(status_counts.keys()), 
                        title="Request Status Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Recent history
            st.subheader("Recent Generations")
            recent = st.session_state.history[-10:]
            
            history_data = []
            for h in recent:
                history_data.append({
                    "Time": h["timestamp"].strftime("%H:%M:%S"),
                    "Prompt": h["prompt"][:30] + "..." if len(h["prompt"]) > 30 else h["prompt"],
                    "Status": h["status"].title(),
                    "Role": h["role"]
                })
            
            df = pd.DataFrame(history_data)
            st.dataframe(df, use_container_width=True)

elif tab == "ℹ️ Help":
    st.subheader("ℹ️ How to Use")
    
    st.markdown("""
    ### 🎯 Quick Start
    1. Select your user role
    2. Enter a description of the image you want
    3. Click "Generate Image"
    4. Download your generated image
    
    ### ✅ Content Guidelines
    - Be descriptive and specific
    - Avoid inappropriate content
    - Use artistic terms for better results
    
    ### 🔧 Technical Notes
    - Demo mode: Creates placeholder images
    - SageMaker mode: Uses real AI model (requires AWS setup)
    - Images are 512x512 pixels
    - Generation takes 10-30 seconds
    
    ### 👥 User Roles
    - **User**: Can generate images
    - **Admin**: Can generate images  
    - **Viewer**: Can only view analytics
    """)

# Footer
st.markdown("---")
st.markdown("Built with Streamlit and Amazon SageMaker")
