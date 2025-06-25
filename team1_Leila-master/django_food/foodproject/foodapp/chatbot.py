from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from django.conf import settings
from .models import ChatSession, ChatMessage, ChatbotKnowledge, Dish, Restaurant, City
from django.utils import timezone
from django.db.models import Q
import json

class MoroccanFoodChatbot:
    def __init__(self, session_id, language='en'):
        self.session = ChatSession.objects.get(session_id=session_id)
        self.language = language
        
        # Initialize the language model
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo",
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # Create the conversation memory
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history",
            input_key="input"
        )
        
        # Define the prompt template based on language
        base_template = self._get_base_template()
        self.prompt = PromptTemplate(
            input_variables=["chat_history", "input"],
            template=base_template
        )
        
        # Create the conversation chain
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            prompt=self.prompt,
            verbose=True
        )
        
        # Load context from database
        self._load_context()
        
        self.load_knowledge_base()

    def _get_base_template(self):
        if self.language == 'fr':
            return """Tu es un expert en cuisine marocaine, aidant les utilisateurs à découvrir la riche culture culinaire du Maroc.
            
            Contexte actuel:
            - Ville sélectionnée: {current_city}
            - Restaurants disponibles: {available_restaurants}
            - Plats populaires: {popular_dishes}

            Historique de la conversation:
            {chat_history}

            Question de l'utilisateur: {input}
            Réponse:"""
        else:
            return """You are a Moroccan cuisine expert, helping users discover Morocco's rich culinary culture.
            
            Current context:
            - Selected city: {current_city}
            - Available restaurants: {available_restaurants}
            - Popular dishes: {popular_dishes}

            Conversation history:
            {chat_history}

            Human: {input}
            Assistant:"""

    def _load_context(self):
        """Load relevant context from database"""
        city = self.session.selected_city
        if city:
            restaurants = Restaurant.objects.filter(city=city)
            dishes = Dish.objects.filter(restaurant__city=city)
        else:
            restaurants = Restaurant.objects.all()[:5]
            dishes = Dish.objects.all()[:5]
        
        self.context = {
            'current_city': city.name if city else 'Not selected',
            'available_restaurants': ', '.join(r.name for r in restaurants),
            'popular_dishes': ', '.join(d.name for d in dishes)
        }

    def get_response(self, user_input):
        """Get a response from the chatbot"""
        try:
            # Update context if needed
            self._load_context()
            
            # Format the input with context
            formatted_input = f"{user_input}\n\nContext: {json.dumps(self.context)}"
            
            # Get response from LangChain
            response = self.conversation.predict(input=formatted_input)
            
            # Save the message to database
            ChatMessage.objects.create(
                session=self.session,
                user_input=user_input,
                bot_response=response,
                context=self.context
            )
            
            return {
                'status': 'success',
                'response': response,
                'context': self.context
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def set_language(self, language_code):
        """Change the chatbot's language"""
        if language_code in ['en', 'fr']:
            self.language = language_code
            # Reinitialize the prompt with new language
            base_template = self._get_base_template()
            self.prompt = PromptTemplate(
                input_variables=["chat_history", "input"],
                template=base_template
            )
            return True
        return False

    def load_knowledge_base(self):
        """Load and prepare the knowledge base for the chatbot"""
        knowledge_texts = []
        for knowledge in ChatbotKnowledge.objects.all():
            content = knowledge.content if self.language == 'en' else knowledge.content_fr
            text = f"Category: {knowledge.get_category_display()}\nTitle: {knowledge.title}\n\n{content}"
            if knowledge.related_dish:
                text += f"\nRelated Dish: {knowledge.related_dish.name}"
            if knowledge.related_city:
                text += f"\nCity: {knowledge.related_city.name}"
            knowledge_texts.append(text)
        
        # Create embeddings and vector store
        embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.knowledge_base = FAISS.from_texts(knowledge_texts, embeddings)
    
    def get_relevant_knowledge(self, query):
        """Retrieve relevant knowledge based on user query"""
        docs = self.knowledge_base.similarity_search(query, k=3)
        return "\n\n".join(doc.page_content for doc in docs)
    
    def get_dish_recommendations(self, city=None):
        """Get dish recommendations based on city"""
        dishes = Dish.objects.all()
        if city:
            dishes = dishes.filter(city=city)
        return dishes[:5]
    
    def get_restaurant_recommendations(self, city=None):
        """Get restaurant recommendations based on city"""
        restaurants = Restaurant.objects.filter(is_open=True)
        if city:
            restaurants = restaurants.filter(city=city)
        return restaurants[:5]
    
    def generate_response(self, user_message):
        """Generate a response to the user's message"""
        # Get relevant knowledge
        knowledge = self.get_relevant_knowledge(user_message)
        
        # Get recommendations if needed
        city = self.session.selected_city
        dishes = self.get_dish_recommendations(city)
        restaurants = self.get_restaurant_recommendations(city)
        
        # Create the system prompt
        system_prompt = f"""You are a knowledgeable and friendly chatbot specializing in Moroccan cuisine and food tourism.
Language: {'French' if self.language == 'fr' else 'English'}

Your knowledge base includes:
{knowledge}

Available recommendations:
Dishes: {', '.join(d.name for d in dishes)}
Restaurants: {', '.join(r.name for r in restaurants)}

Please provide helpful, accurate information about Moroccan food, dishes, and dining culture. 
If suggesting dishes or restaurants, use the ones listed above.
Keep responses concise but informative, and maintain a friendly, conversational tone.
"""
        
        # Create the conversation chain
        prompt = PromptTemplate(
            input_variables=["history", "input"],
            template=system_prompt + "\n\nCurrent conversation:\n{history}\nHuman: {input}\nAssistant:"
        )
        
        chain = ConversationChain(
            llm=self.llm,
            prompt=prompt,
            memory=self.memory,
            verbose=True
        )
        
        # Generate response
        response = chain.predict(input=user_message)
        
        # Save the interaction
        ChatMessage.objects.create(
            session=self.session,
            role='user',
            content=user_message
        )
        ChatMessage.objects.create(
            session=self.session,
            role='assistant',
            content=response
        )
        
        # Update session
        self.session.last_interaction = timezone.now()
        self.session.save()
        
        return response
    
    def switch_language(self, language):
        """Switch the chatbot's language"""
        if language in ['en', 'fr']:
            self.language = language
            self.session.language = language
            self.session.save()
            
            # Return a confirmation message in the new language
            if language == 'fr':
                return "La langue a été changée en français. Comment puis-je vous aider?"
            else:
                return "Language has been switched to English. How can I help you?"
        return "Unsupported language" 